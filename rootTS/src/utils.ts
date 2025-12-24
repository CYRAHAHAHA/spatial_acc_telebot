import { Request, Response, NextFunction } from "express";
import path from "path";
import fs from "fs";
import { parse } from "csv-parse/sync";
import { stringify } from "csv-stringify/sync";
import { app } from "./app";

// Extend Express Session to hold token
declare module "express-session" {
  interface SessionData {
    access_token?: string;
    aggregatedData?: any;
  }
}

// ============ Auth Decorator/Middleware ============

export const requireAccessToken = (
  passToken = false,
  msg = "Please configure Autodesk credentials and authenticate."
) => {
  return async (req: Request, res: Response, next: NextFunction) => {
    const auth = app.get("autodesk_auth"); // Retrieve from app settings
    let token: string | null = null;

    if (auth) {
      // Always reload from file
      auth.load_tokens();
      token = await auth.get_access_token();
    }

    if (!token) {
      const encodedMsg = encodeURIComponent(msg);
      return res.redirect(`/?msg=${encodedMsg}`);
    }

    if (req.session) {
      req.session.access_token = token;
    }

    if (passToken) {
      // In Express, we attach data to `req` object, not kwargs
      (req as any).token = token;
    }

    next();
  };
};

// ============ File/Path Utility Functions ============

export const getPersistentDir = (subdir: string = ""): string => {
  let base: string;
  if (process.env.RAILWAY_ENVIRONMENT) {
    // Railway deployment - use mounted volume
    base = path.resolve("/app/data");
  } else {
    // Local development - use workspace data directory (project_root/data)
    base = path.resolve(__dirname, "../data");
  }

  if (!fs.existsSync(base)) fs.mkdirSync(base, { recursive: true });

  if (subdir) {
    const fullPath = path.join(base, subdir);
    if (!fs.existsSync(fullPath)) fs.mkdirSync(fullPath, { recursive: true });
    return fullPath;
  }

  return base;
};

export const getDataDir = (): string => {
  return getPersistentDir();
};

export const getOutputDir = (): string => {
  if (process.env.RAILWAY_ENVIRONMENT) {
    // On Railway, use persistent volume for output too
    return getPersistentDir("output");
  } else {
    // Local development - use root/output
    const out = path.resolve(__dirname, "../output");
    if (!fs.existsSync(out)) fs.mkdirSync(out, { recursive: true });
    return out;
  }
};

export const getTokenFilePath = (): string => {
  if (process.env.RAILWAY_ENVIRONMENT) {
    return path.join(getPersistentDir(), "autodesk_tokens.json");
  } else {
    return path.resolve(__dirname, "../autodesk_tokens.json");
  }
};

export const getCsvPath = (filename: string): string => {
  return path.join(getDataDir(), filename);
};

// ============ CSV Logic Functions ============

export const readStatusSetsCsv = (
  projectId: string
): Record<string, string> => {
  const csvPath = getCsvPath("status_sets.csv");
  const mapping: Record<string, string> = {};

  if (!fs.existsSync(csvPath)) {
    console.log(`Status sets CSV not found at ${csvPath}`);
    return mapping;
  }

  try {
    const content = fs.readFileSync(csvPath, "utf-8");
    const records = parse(content, { columns: true, skip_empty_lines: true });

    for (const row of records) {
      const name = (row.status_set_name || "").trim();
      const sid = (row.status_set_id || "").trim();
      const proj = (row.project_id || "").trim();

      if (!name || !sid) continue;

      // Keep first match for a given name
      if (!(name in mapping)) {
        mapping[name] = sid;
      }

      // If a row matches current project, override to ensure correct one
      if (proj === projectId) {
        mapping[name] = sid;
      }
    }
  } catch (ex) {
    console.log(`Failed to read status sets CSV: ${ex}`);
  }
  return mapping;
};

export const readCustomFieldsCsv = (
  projectId: string
): Record<string, string> => {
  const csvPath = getCsvPath("custom_fields.csv");
  const mapping: Record<string, string> = {};

  if (!fs.existsSync(csvPath)) {
    console.log(`Custom fields CSV not found at ${csvPath}`);
    return mapping;
  }

  try {
    const content = fs.readFileSync(csvPath, "utf-8");
    const records = parse(content, { columns: true, skip_empty_lines: true });

    for (const row of records) {
      const proj = (row.project_id || "").trim();
      const attrId = (row.custom_attribute_id || "").trim();
      const name = (row.name || "").trim();
      const display = (row.display_name || "").trim();

      if (!attrId) continue;

      // Map both name and display name to id
      if (display && !(display in mapping)) mapping[display] = attrId;
      if (name && !(name in mapping)) mapping[name] = attrId;

      // Prefer entries matching project_id
      if (proj === projectId) {
        if (display) mapping[display] = attrId;
        if (name) mapping[name] = attrId;
      }
    }
  } catch (ex) {
    console.log(`Failed to read custom fields CSV: ${ex}`);
  }
  return mapping;
};

export const readCategoriesCsv = (
  projectId: string
): Record<string, string> => {
  const csvPath = getCsvPath("categories.csv");
  const mapping: Record<string, string> = {};

  if (!fs.existsSync(csvPath)) {
    console.log(`Categories CSV not found at ${csvPath}`);
    return mapping;
  }

  try {
    const content = fs.readFileSync(csvPath, "utf-8");
    const records = parse(content, { columns: true, skip_empty_lines: true });

    for (const row of records) {
      const proj = (row.project_id || "").trim();
      const catId = (row.category_id || "").trim();
      const catName = (row.category_name || "").trim();

      if (!catId || !catName) continue;

      // Keep first match for a given name
      if (!(catName in mapping)) {
        mapping[catName] = catId;
      }

      // Prefer entries matching project_id
      if (proj === projectId) {
        mapping[catName] = catId;
      }
    }
  } catch (ex) {
    console.log(`Failed to read categories CSV: ${ex}`);
  }
  return mapping;
};

export const writeCsv = (
  filename: string,
  data: Record<string, any>[],
  headers: string[]
): void => {
  const csvPath = getCsvPath(filename);
  const dir = path.dirname(csvPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  try {
    // Format data: handle boolean conversion and nulls/undefined
    const formattedData = data.map((row) => {
      const newRow: Record<string, any> = {};
      for (const key of headers) {
        const val = row[key];
        if (val === null || val === undefined) {
          newRow[key] = "";
        } else if (typeof val === "boolean") {
          newRow[key] = val ? "True" : "False";
        } else {
          newRow[key] = String(val); // Convert numbers/etc to string
        }
      }
      return newRow;
    });

    const output = stringify(formattedData, {
      header: true,
      columns: headers,
      bom: true, // Matches encoding='utf-8-sig'
    });

    fs.writeFileSync(csvPath, output);
    console.log(`Successfully wrote ${data.length} rows to ${csvPath}`);
  } catch (ex) {
    console.log(`Failed to write CSV ${filename}: ${ex}`);
    throw ex;
  }
};
