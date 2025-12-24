import axios from 'axios';
import fs from 'fs';
import path from 'path';
import querystring from 'querystring';

export class AutodeskAuth {
    client_id: string;
    client_secret: string;
    redirect_uri: string;
    scopes: string;
    token_file: string;
    access_token: string | null = null;
    refresh_token: string | null = null;
    expires_at: string | null = null;

    constructor(client_id: string, client_secret: string, redirect_uri: string, scopes: string) {
        this.client_id = client_id;
        this.client_secret = client_secret;
        this.redirect_uri = redirect_uri;
        this.scopes = scopes;
        if (process.env.RAILWAY_ENVIRONMENT) {
            const tokenDir = path.resolve('/app/data');
            if (!fs.existsSync(tokenDir)) fs.mkdirSync(tokenDir, { recursive: true });
            this.token_file = path.join(tokenDir, "autodesk_tokens.json");
        } else {
            this.token_file = path.resolve(__dirname, "../autodesk_tokens.json");
        }
        this.load_tokens();
    }

    save_tokens(access_token: string, refresh_token: string, expires_in: number) {
        this.access_token = access_token;
        this.refresh_token = refresh_token;
        const now = new Date();
        this.expires_at = new Date(now.getTime() + (expires_in - 300) * 1000).toISOString();
        fs.writeFileSync(this.token_file, JSON.stringify({
            access_token, refresh_token, expires_at: this.expires_at
        }, null, 2));
    }

    load_tokens(): boolean {
        if (!fs.existsSync(this.token_file)) return false;
        try {
            const data = JSON.parse(fs.readFileSync(this.token_file, 'utf-8'));
            this.access_token = data.access_token;
            this.refresh_token = data.refresh_token;
            this.expires_at = data.expires_at;
            return true;
        } catch (e) { return false; }
    }

    is_token_valid(): boolean {
        if (!this.access_token || !this.expires_at) return false;
        return new Date() < new Date(this.expires_at);
    }

    async get_access_token(): Promise<string | null> {
        if (this.is_token_valid()) return this.access_token;
        if (this.refresh_token) return await this.refresh_access_token();
        return null;
    }

    async exchange_code_for_tokens(code: string): Promise<string | null> {
        const url = "https://developer.api.autodesk.com/authentication/v2/token";
        const data = querystring.stringify({
            client_id: this.client_id, client_secret: this.client_secret,
            grant_type: "authorization_code", code, redirect_uri: this.redirect_uri
        });
        try {
            const res = await axios.post(url, data);
            this.save_tokens(res.data.access_token, res.data.refresh_token, res.data.expires_in);
            return this.access_token;
        } catch (e) { return null; }
    }

    async refresh_access_token(): Promise<string | null> {
        if (!this.refresh_token) return null;
        const url = "https://developer.api.autodesk.com/authentication/v2/token";
        const data = querystring.stringify({
            client_id: this.client_id, client_secret: this.client_secret,
            grant_type: "refresh_token", refresh_token: this.refresh_token
        });
        try {
            const res = await axios.post(url, data);
            this.save_tokens(res.data.access_token, res.data.refresh_token, res.data.expires_in);
            return this.access_token;
        } catch (e) {
            if (fs.existsSync(this.token_file)) fs.unlinkSync(this.token_file);
            return null;
        }
    }

    get_auth_url(): string {
        return `https://developer.api.autodesk.com/authentication/v2/authorize?response_type=code&client_id=${this.client_id}&redirect_uri=${querystring.escape(this.redirect_uri)}&scope=${querystring.escape(this.scopes)}`;
    }
}