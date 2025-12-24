import axios from 'axios';
import { config } from '../config';

export async function fetchIssueSubtypes(token: string) {
    const subtypes: any = {};
    const head = { Authorization: `Bearer ${token}` };
    try {
        const r = await axios.get(`https://developer.api.autodesk.com/issues/v1/projects/${config.project_id}/issue-types`, { headers: head });
        (r.data.results || []).forEach((t: any) => {
            (t.subtypes || []).forEach((s: any) => {
                subtypes[s.id] = { type: t.title, subtype: s.title, source: "Config" };
            });
        });
    } catch(e) {}
    
    // Fallback if empty
    if(!Object.keys(subtypes).length) {
         try {
            const r = await axios.get(`https://developer.api.autodesk.com/construction/issues/v1/projects/${config.project_id}/issues`, { headers: head });
            (r.data.results || []).forEach((i: any) => {
                if(i.issueSubtypeId) subtypes[i.issueSubtypeId] = { type: i.issueTypeName, subtype: i.issueSubtypeName, source: "Issue" };
            });
         } catch(e) {}
    }
    return subtypes;
}

export function formatSubtypesOutput(subtypes: any) {
    const grp: any = {};
    Object.entries(subtypes).forEach(([id, v]: any) => {
        if(!grp[v.type]) grp[v.type] = [];
        grp[v.type].push({ ...v, id });
    });
    return ["", grp];
}