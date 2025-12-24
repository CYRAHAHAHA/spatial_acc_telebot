import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { Response } from 'express';
import { stringify } from 'csv-stringify/sync';
import { parse } from 'csv-parse/sync';
import { config } from '../config';
import { getCsvPath, getOutputDir, getDataDir } from '../utils';

export async function fetchAllAssetsInfo(res: Response, token: string) {
    console.log("Fetching all assets info...");
    const projId = config.project_id;
    const limit = 200;
    let offset = 0;
    const allAssets: any[] = [];
    
    try {
        while(true) {
            const r = await axios.get(`https://developer.api.autodesk.com/construction/assets/v2/projects/${projId}/assets`, {
                headers: { Authorization: `Bearer ${token}` }, params: { includeCustomAttributes: "true", limit, offset }
            });
            const recs = r.data.results || [];
            if(!recs.length) break;
            allAssets.push(...recs);
            if(recs.length < limit) break;
            offset += limit;
        }

        // Write raw
        fs.writeFileSync(path.join(getOutputDir(), "assets_raw.json"), JSON.stringify({ results: allAssets }, null, 2));

        // Logic to get IFCGlobalId name from custom_fields.csv
        let ifcName = "";
        if(fs.existsSync(getCsvPath("custom_fields.csv"))) {
            const rows = parse(fs.readFileSync(getCsvPath("custom_fields.csv")), { columns: true });
            const f = rows.find((r: any) => r.display_name === "IFCGlobalId");
            if(f) ifcName = f.name;
        }

        // Logic to map category -> status set
        const catMap: any = {};
        if(fs.existsSync(getCsvPath("categories.csv"))) {
            const rows = parse(fs.readFileSync(getCsvPath("categories.csv")), { columns: true });
            rows.forEach((r: any) => { if(r.category_id && r.status_set_id) catMap[r.category_id] = r.status_set_id; });
        }

        const csvData = allAssets.map(a => ({
            B3F_id: a.id, description: a.description, companyId: a.companyId, clientAssetId: a.clientAssetId,
            category_id: a.categoryId, status_set_id: catMap[a.categoryId] || "", status_id: a.statusId,
            ifc_global_id: (a.customAttributes || {})[ifcName] || ""
        }));

        fs.writeFileSync(getCsvPath("assets_total.csv"), stringify(csvData, { header: true }));
        res.redirect(`/?msg=${encodeURIComponent("Assets fetched " + allAssets.length)}`);
    } catch(e: any) { res.status(502).json({ error: e.message }); }
}