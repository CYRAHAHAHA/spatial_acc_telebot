import axios from 'axios';
import fs from 'fs';
import { parse } from 'csv-parse/sync';
import { config } from '../config';
import { getCsvPath } from '../utils';

export async function updateAssets(token: string, guid: string, statusVal: string) {
    // 1. Resolve asset info
    if(!fs.existsSync(getCsvPath("assets_total.csv"))) return { status: 404, data: { error: "No assets CSV" } };
    const assets = parse(fs.readFileSync(getCsvPath("assets_total.csv")), { columns: true });
    const asset = assets.find((a: any) => a.ifc_global_id === guid);
    if(!asset) return { status: 404, data: { error: "Asset not found" } };

    // 2. Resolve status ID
    if(!fs.existsSync(getCsvPath("status_sets.csv"))) return { status: 404, data: { error: "No status sets CSV" } };
    const statuses = parse(fs.readFileSync(getCsvPath("status_sets.csv")), { columns: true });
    const st = statuses.find((s: any) => s.status_set_id === asset.status_set_id && s.status_label === statusVal);
    if(!st) return { status: 404, data: { error: "Status not found" } };

    // 3. Patch
    try {
        const body = { [asset.B3F_id]: { statusId: st.status_id } };
        const r = await axios.patch(`https://developer.api.autodesk.com/construction/assets/v2/projects/${config.project_id}/assets:batch-patch`, 
            body, { headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } });
        return { status: r.status, data: r.data };
    } catch(e: any) { return { status: 502, data: { error: e.message } }; }
}