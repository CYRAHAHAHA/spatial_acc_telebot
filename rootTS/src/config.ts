import dotenv from 'dotenv';
import path from 'path';
import fs from 'fs';

const dotenvPath = path.resolve(__dirname, '../../.env');
const isRailway = !!process.env.RAILWAY_ENVIRONMENT;

if (!isRailway) {
    if (fs.existsSync(dotenvPath)) {
        dotenv.config({ path: dotenvPath });
    }
} else {
    if (fs.existsSync(dotenvPath)) {
        dotenv.config({ path: dotenvPath });
    }
}

class Config {
    REQUIRED_VARS = ["CLIENT_ID", "CLIENT_SECRET", "SCOPES", "PROJECT_ID", "TELEGRAM_TOKEN", "OPENAI_API_KEY"];
    client_id: string;
    client_secret: string;
    scopes: string;
    project_id: string;
    root_id: string;
    openai_api_key: string;
    telegram_token: string;
    railway_environment?: string;
    railway_public_domain?: string;
    railway_static_url?: string;
    port: number;
    redirect_uri: string;
    user?: string;

    constructor() {
        this.client_id = process.env.CLIENT_ID || "";
        this.client_secret = process.env.CLIENT_SECRET || "";
        this.scopes = process.env.SCOPES || "";
        this.project_id = process.env.PROJECT_ID || "";
        this.root_id = process.env.ROOT_FOLDER_ID || "";
        this.openai_api_key = process.env.OPENAI_API_KEY || "";
        this.telegram_token = process.env.TELEGRAM_TOKEN || "";
        this.railway_environment = process.env.RAILWAY_ENVIRONMENT;
        this.railway_public_domain = process.env.RAILWAY_PUBLIC_DOMAIN;
        this.railway_static_url = process.env.RAILWAY_STATIC_URL;
        this.port = parseInt(process.env.PORT || "8080", 10);
        this.redirect_uri = this._get_redirect_uri();
        this.user = process.env.USER || "";
        this._validate_env();
    }

    _get_redirect_uri(): string {
        if (process.env.REDIRECT_URI) return process.env.REDIRECT_URI;
        if (this.railway_public_domain) return `https://${this.railway_public_domain}/callback`;
        if (this.railway_static_url) return `${this.railway_static_url}/callback`;
        return "http://localhost:8080/callback";
    }

    is_railway(): boolean {
        return !!this.railway_environment;
    }

    _validate_env() {
        const missing = this.REQUIRED_VARS.filter(v => !process.env[v]);
        if (missing.length > 0) {
            console.error(`ERROR: Missing vars: ${missing.join(', ')}`);
            if (!this.is_railway()) process.exit(1);
        }
    }
}

export const config = new Config();