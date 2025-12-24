import express from 'express';
import session from 'express-session';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { parse } from 'csv-parse/sync';
import { config } from './config';
import { AutodeskAuth } from './authentication';
import { getCsvPath } from './utils';

export const app = express();

app.use(session({ secret: 'supersecretkey', resave: false, saveUninitialized: true }));
app.use(cors({ origin: true, credentials: true }));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '../src')));

const auth = new AutodeskAuth(config.client_id, config.client_secret, config.redirect_uri, config.scopes || "data:read data:write data:create");
app.set('autodesk_auth', auth);

app.get('/', (req, res) => res.sendFile(path.join(__dirname, '../src/index.html')));

app.get('/api/status', (req, res) => {
    const authInstance = app.get('autodesk_auth');
    try { authInstance.load_tokens(); } catch (e) {}
    const tokenValid = authInstance.is_token_valid();
    const env: any = {};
    for (const [k, v] of Object.entries(config)) {
        if (!k.startsWith('__') && typeof v !== 'function') env[k] = v;
    }
    res.json({
        user: config.user || "",
        token: { valid: tokenValid, expiresAt: authInstance.expires_at },
        env,
        message: req.query.msg || ""
    });
});

app.get('/api/categories', (req, res) => {
    const csvPath = getCsvPath("categories.csv");
    if (!fs.existsSync(csvPath)) return res.json({ count: 0, categories: [], tree: [] });
    try {
        const content = fs.readFileSync(csvPath, 'utf-8');
        const categories = parse(content, { columns: true, skip_empty_lines: true }).map((row: any) => ({
            projectId: row.project_id, categoryId: row.category_id, categoryName: row.category_name,
            parentId: row.parent_id, statusSetId: row.status_set_id, statusSetName: row.status_set_name,
            customAttributes: row.custom_attributes
        }));
        const byId: any = {};
        categories.forEach((c: any) => byId[c.categoryId] = { ...c, children: [] });
        categories.forEach((c: any) => { if (c.parentId && byId[c.parentId]) byId[c.parentId].children.push(c.categoryId); });
        const roots = Object.values(byId).filter((c: any) => !c.parentId);
        const buildTree = (node: any): any => ({
            categoryId: node.categoryId, categoryName: node.categoryName, statusSetName: node.statusSetName,
            statusSetId: node.statusSetId, parentId: node.parentId,
            customAttributes: node.customAttributes ? node.customAttributes.split(';').filter(Boolean) : [],
            children: node.children.map((childId: string) => buildTree(byId[childId]))
        });
        res.json({ count: categories.length, categories, tree: roots.map(buildTree) });
    } catch (ex) { res.status(500).json({ error: String(ex) }); }
});

import { router as apiRoutes } from './routes';
app.use('/', apiRoutes);