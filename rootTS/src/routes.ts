import { Router, Request, Response } from 'express';
import { app } from './app';
import { requireAccessToken } from './utils';
import { config } from './config';
import { AutodeskAuth } from './authentication';
import axios from 'axios';
import path from 'path';

import { fetchAssetsConfig } from './functions/fetchAssetsConfig';
import { fetchAllAssetsInfo } from './functions/fetchAllAssetsInfo';
import { updateAssets } from './functions/updateStatus';
import { updateIssue } from './functions/updateIssue';
import { createIssue } from './functions/createIssue';
import { fetchIssueSubtypes, formatSubtypesOutput } from './functions/fetchIssueSubtypes';
import { fetchIfcMetadata } from './functions/fetchMetadata';
import { discoverRootFolder } from './functions/getRootFolderId';

export const router = Router();

router.get('/do_all_initial_setup', requireAccessToken(true), async (req: Request, res: Response) => {
    const token = (req as any).token;
    // Note: We pass req, res because fetchAssetsConfig modifies session and returns redirect
    // Since we want to chain them, we might need to adjust logic or just call them sequentially ignoring redirects
    // For 1:1 functional copy where original did redirect at the end:
    console.log("Starting initial setup: fetching assets config...");
    await fetchAssetsConfig(req, { ...res, redirect: () => {} } as any, token); 
    console.log("Should have fetched assets config, with CSVs: categories, custom fields, status sets.");
    console.log("Now fetching all assets info...");
    await fetchAllAssetsInfo({ ...res, redirect: () => {} } as any, token);
    await fetchIfcMetadata({ ...res, redirect: () => {} } as any, token);
    res.redirect(`/?msg=${encodeURIComponent("All initial setup functions called successfully")}`);
});

router.get('/data/:filename', (req, res) => {
    res.sendFile(path.join(path.resolve(__dirname, '../data'), req.params.filename));
});

router.get('/authorize', (req, res) => {
    const auth = app.get('autodesk_auth');
    res.redirect(auth.get_auth_url());
});

router.get('/callback', async (req, res) => {
    const code = req.query.code as string;
    if (!code) return res.redirect("/?msg=No+code");
    const auth = app.get('autodesk_auth');
    const token = await auth.exchange_code_for_tokens(code);
    if (!token) return res.redirect("/?msg=Token+failed");
    if (req.session) req.session.access_token = token;
    res.redirect("/?msg=Authenticated");
});

router.get('/fetch_assets_config', requireAccessToken(true), async (req, res) => {
    await fetchAssetsConfig(req, res, (req as any).token);
});

router.get('/fetch_all_assets_info', requireAccessToken(true), async (req, res) => {
    await fetchAllAssetsInfo(res, (req as any).token);
});

router.post('/update_status', requireAccessToken(true), async (req, res) => {
    const { asset_guid, status_value } = req.body;
    const token = (req as any).token;
    if (!status_value || !asset_guid) return res.status(400).json({ error: "Missing guid or status" });
    
    const guids = Array.isArray(asset_guid) ? asset_guid : [asset_guid];
    const results = [];
    let success = 0;

    for (const g of guids) {
        const r = await updateAssets(token, g, status_value);
        if (r.status === 200) success++;
        results.push({ asset_guid: g, result: r.data });
    }
    res.json({ success: true, total: guids.length, successful: success, results });
});

router.post('/update_issue_status', requireAccessToken(true), async (req, res) => {
    const { issue_guid, status_value } = req.body;
    const token = (req as any).token;
    const result = await updateIssue(token, issue_guid, status_value);
    res.status(result.status).json(result.data);
});

router.post('/create_issue', requireAccessToken(true), async (req, res) => {
    const { title, status, issue_subtype_id, description, location_description } = req.body;
    const token = (req as any).token;
    const result = await createIssue(token, title, status, issue_subtype_id, undefined, description, undefined, location_description);
    res.status(result.status).json(result.data);
});

router.get('/fetch_issue_subtypes', requireAccessToken(true), async (req, res) => {
    const token = (req as any).token;
    try {
        const subtypes = await fetchIssueSubtypes(token);
        const [_, grouped] = formatSubtypesOutput(subtypes);
        
        let recentIssues: any[] = [];
        if (config.project_id) {
            try {
                const r = await axios.get(`https://developer.api.autodesk.com/construction/issues/v1/projects/${config.project_id}/issues`, {
                    headers: { Authorization: `Bearer ${token}` }, params: { limit: 20 }
                });
                recentIssues = r.data.results || r.data.data || [];
            } catch (e) {}
        }
        res.json({ success: true, total_count: Object.keys(subtypes).length, grouped_by_type: grouped, recent_issues: recentIssues });
    } catch (e: any) { res.status(500).json({ error: e.message }); }
});

router.get('/fetch_metadata', requireAccessToken(true), async (req, res) => {
    await fetchIfcMetadata(res, (req as any).token);
});

router.get('/get_root_folder_id', requireAccessToken(true), async (req, res) => {
    try {
        const result = await discoverRootFolder((req as any).token);
        res.json(result);
    } catch (e: any) { res.status(500).json({ error: e.message }); }
});