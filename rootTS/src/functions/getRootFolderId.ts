import axios from 'axios';
import { config } from '../config';

export async function discoverRootFolder(token: string) {
    const head = { Authorization: `Bearer ${token}` };
    const h = await axios.get("https://developer.api.autodesk.com/project/v1/hubs", { headers: head });
    const hubId = h.data.data[0].id;
    const projId = config.project_id.startsWith("b.") ? config.project_id : "b." + config.project_id;
    
    const f = await axios.get(`https://developer.api.autodesk.com/project/v1/hubs/${hubId}/projects/${projId}/topFolders`, { headers: head });
    const root = f.data.data.find((x: any) => x.attributes.name === "Project Files") || f.data.data[0];
    
    return { hub_id: hubId, project_id: projId, root_folder_id: root.id };
}