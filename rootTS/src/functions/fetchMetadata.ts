import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { Response } from 'express';
import { config } from '../config';
import { getDataDir } from '../utils';

export async function fetchIfcMetadata(res: Response, token: string) {
    // simplified 1:1 logic
    const hubUrl = "https://developer.api.autodesk.com/project/v1/hubs";
    const head = { Authorization: `Bearer ${token}` };
    
    try {
        // Logic would traverse folders to find .ifc, get URN, call model derivative...
        // For copy purposes, we log that we are starting
        console.log("Starting metadata fetch...");
        // ... (Full implementation requires valid URNs and translation jobs)
        res.redirect(`/?msg=${encodeURIComponent("Metadata fetch started (Mock)")}`);
    } catch(e: any) { res.redirect(`/?msg=Error`); }
}