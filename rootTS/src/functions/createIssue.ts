import axios from 'axios';
import { config } from '../config';
const API_BASE = "https://developer.api.autodesk.com/construction/issues/v1/projects";

export async function createIssue(token: string, title: string, status: string, subtypeId?: string, ownerId?: string, desc?: string, date?: string, locDesc?: string) {
    const projId = config.project_id;
    if (!title || !status) return { status: 400, data: { error: "Missing fields" } };
    
    // Simple owner ID fetch
    if (!ownerId) {
        try {
            const u = await axios.get("https://developer.api.autodesk.com/userprofile/v1/users/@me", { headers: { Authorization: `Bearer ${token}` } });
            ownerId = u.data.userId;
        } catch(e) { return { status: 500, data: { error: "Cannot get user" } }; }
    }

    if (!subtypeId) {
        // Simple subtype discovery
        try {
            const r = await axios.get(`${API_BASE}/${projId}/issues`, { headers: { Authorization: `Bearer ${token}` } });
            const subs: any = {};
            (r.data.results || []).forEach((i: any) => { if(i.issueSubtypeId) subs[i.issueSubtypeId] = { type: i.issueTypeName, subtype: i.issueSubtypeName }; });
            return { status: 400, data: { error: "Missing subtypeId", available: subs } };
        } catch(e) { return { status: 400, data: { error: "Missing subtypeId" } }; }
    }

    const payload: any = { title, status, ownerId, issueSubtypeId: subtypeId };
    if (desc) payload.description = desc;
    if (locDesc) payload.locationDescription = locDesc;

    try {
        const res = await axios.post(`${API_BASE}/${projId}/issues`, payload, { headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } });
        return { status: res.status, data: res.data };
    } catch (e: any) { return { status: 502, data: { error: e.message } }; }
}