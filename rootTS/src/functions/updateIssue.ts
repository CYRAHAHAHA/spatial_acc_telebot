import axios from 'axios';
import { config } from '../config';

export async function updateIssue(token: string, guid: string, status: string) {
    if(!guid || !status) return { status: 400, data: { error: "Missing fields" } };
    try {
        const r = await axios.patch(`https://developer.api.autodesk.com/construction/issues/v1/projects/${config.project_id}/issues/${guid}`, 
            { status }, { headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } });
        return { status: r.status, data: r.data };
    } catch(e: any) { return { status: 502, data: { error: e.message } }; }
}