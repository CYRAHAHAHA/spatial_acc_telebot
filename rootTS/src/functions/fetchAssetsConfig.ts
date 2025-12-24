import axios from "axios";
import fs from "fs";
import path from "path";
import { Request, Response } from "express";
import { stringify } from "csv-stringify/sync";
import { config } from "../config";
import { getCsvPath, getOutputDir, writeCsv } from "../utils"; // Assuming writeCsv is exported, or I will use local helper below

// Helper to match Python's write_csv behavior (UTF-8 SIG for Excel)
function saveCsv(filename: string, data: any[], columns: string[]) {
  const csvPath = getCsvPath(filename);
  const output = stringify(data, {
    header: true,
    columns: columns,
    bom: true, // Matches encoding='utf-8-sig'
  });
  fs.writeFileSync(csvPath, output);
}

export async function fetchAssetsConfig(
  req: Request,
  res: Response,
  accessToken: string
) {
  const projectId = config.project_id;
  const baseUrl =
    "https://developer.api.autodesk.com/construction/assets/v1/projects";

  const headers = {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  try {
    // === 1️⃣ Fetch custom attributes ===
    let customAttributes: any[] = [];
    try {
      const caResp = await axios.get(
        `${baseUrl}/${projectId}/custom-attributes`,
        { headers }
      );
      if (caResp.status === 200) customAttributes = caResp.data.results || [];
    } catch (e) {
      console.error("Error fetching custom attributes", e);
    }

    // === 2️⃣ Fetch status-step sets ===
    let statusSetsRaw: any[] = [];
    try {
      const ssResp = await axios.get(
        `${baseUrl}/${projectId}/status-step-sets`,
        { headers }
      );
      if (ssResp.status === 200) statusSetsRaw = ssResp.data.results || [];
    } catch (e) {
      console.error("Error fetching status sets", e);
    }

    const statusSets: any[] = [];
    const statusSetsDict: Record<string, any> = {};

    for (const ss of statusSetsRaw) {
      const ssObj = {
        projectId: ss.projectId,
        id: ss.id,
        name: ss.name,
        description: ss.description || "",
        statuses: ss.values || [],
      };
      statusSets.push(ssObj);
      statusSetsDict[ss.id] = ssObj;
    }

    // === 3️⃣ Fetch raw categories ===
    let categoriesRaw: any[] = [];
    try {
      const catResp = await axios.get(`${baseUrl}/${projectId}/categories`, {
        headers,
      });
      if (catResp.status === 200) categoriesRaw = catResp.data.results || [];
    } catch (e) {
      console.error("Error fetching categories", e);
    }

    // === 4️⃣ Fetch category → status set mappings using batch API ===
    const categoryIds = categoriesRaw.map((cat: any) => cat.id);
    const batchUrl = `${baseUrl}/${projectId}/category-status-step-sets/status-step-sets:batch-get`;
    const batchPayload = { ids: categoryIds };

    console.log(
      "Fetching category to status set mappings via batch API...",
      batchPayload
    );

    let categoryStatusRaw: any[] = [];
    try {
      const batchResp = await axios.post(batchUrl, batchPayload, {
        headers,
        params: { includeInherited: "true" },
      });
      if (batchResp.status === 200)
        categoryStatusRaw = batchResp.data.results || [];
    } catch (e) {
      console.error("Error batch fetching mappings", e);
    }

    console.log("GOTCHA");
    // Build a mapping: categoryId -> statusStepSetId
    const categoryToStatusSet: Record<string, string> = {};
    for (const c of categoryStatusRaw) {
      categoryToStatusSet[c.categoryId] = c.statusStepSetId;
    }

    // === 5️⃣ Map categories with their status sets and custom attributes ===
    const categoriesWithStatus: any[] = [];
    for (const cat of categoriesRaw) {
      const statusSetId = categoryToStatusSet[cat.id];
      const statusSet = statusSetsDict[statusSetId];

      // Determine display name for root/system categories
      const statusSetName = statusSet
        ? statusSet.name
        : "No Status Set (system)";
      const statuses = statusSet ? statusSet.statuses : [];

      const categoryCustomAttributes = customAttributes.map((ca: any) => ({
        displayName: ca.displayName,
        description: ca.description,
        dataType: ca.dataType,
        enumValues: ca.enumValues || [],
      }));

      categoriesWithStatus.push({
        categoryName: cat.name,
        categoryId: cat.id,
        parentId: cat.parentId,
        statusSetId: statusSetId,
        statusSetName: statusSetName,
        statuses: statuses,
        customAttributes: categoryCustomAttributes,
        children: cat.subcategoryIds || [],
      });
    }

    // === 6️⃣ Aggregate data ===
    const aggregatedData = {
      customAttributes: customAttributes.map((ca: any) => ({
        [ca.displayName]: ca.description || "",
        id: ca.id,
      })),
      statusSets: statusSets,
      categories: categoriesWithStatus,
    };

    // Store in session
    if (req.session) {
      (req.session as any).aggregated_data = aggregatedData;
    }

    // === 7️⃣ Save all raw and mapped data to log.json ===
    const logPath = path.join(getOutputDir(), "log.json");
    fs.writeFileSync(
      logPath,
      JSON.stringify(
        {
          customAttributesRaw: customAttributes,
          statusSetsRaw: statusSetsRaw,
          categoriesRaw: categoriesRaw,
          categoryStatusMappingRaw: categoryStatusRaw,
          categoriesWithStatus: categoriesWithStatus,
        },
        null,
        2
      )
    );

    console.log("\n=== Saved log.json with all debug info ===");
    console.log(logPath);

    // === 8️⃣ Save aggregated data to log_aggregated.json ===
    const logAggPath = path.join(getOutputDir(), "log_aggregated.json");
    fs.writeFileSync(logAggPath, JSON.stringify(aggregatedData, null, 2));
    console.log("\n=== Saved log_aggregated.json with aggregated data ===");

    const msg = encodeURIComponent(
      `Fetched ${customAttributes.length} attributes, ` +
        `${statusSets.length} status sets, ` +
        `${categoriesRaw.length} categories`
    );

    // === 8️⃣ Save useful data to CSVs ===

    // --- Status Sets CSV ---
    const statusSetsCsv: any[] = [];
    for (const ss of statusSets) {
      for (const status of ss.statuses) {
        statusSetsCsv.push({
          project_id: ss.projectId,
          status_set_id: ss.id,
          status_set_name: ss.name,
          status_id: status.id,
          status_label: status.label,
          status_description: status.description || "",
        });
      }
    }

    saveCsv("status_sets.csv", statusSetsCsv, [
      "project_id",
      "status_set_id",
      "status_set_name",
      "status_id",
      "status_label",
      "status_description",
    ]);
    console.log("\n=== Saved status_sets.csv with status sets data ===");

    // --- Custom Fields CSV ---
    const customFieldsCsv: any[] = [];
    for (const ca of customAttributes) {
      // keep semicolons inside the cell to separate multiple values
      let valuesRaw = "";
      if (ca.dataType === "enum") {
        const ev = ca.enumValues || [];
        // enumValues can be strings or objects; stringify safely
        valuesRaw = ev
          .map((v: any) => (typeof v === "string" ? v : String(v)))
          .join(";");
      }

      let valuesAndIdsRaw = "";
      if (ca.values) {
        valuesAndIdsRaw = (ca.values || [])
          .map((value: any) => {
            const disp = (value.displayName || "").trim();
            const id = (value.id || "").trim();
            return `${disp}(${id})`;
          })
          .join(";");
      }

      customFieldsCsv.push({
        project_id: ca.projectId,
        custom_attribute_id: ca.id,
        name: ca.name,
        display_name: ca.displayName,
        description: ca.description || "",
        data_type: ca.dataType,
        required: ca.requiredOnIngress ? "True" : "False",
        values: valuesRaw,
        values_and_ids: valuesAndIdsRaw,
      });
    }

    saveCsv("custom_fields.csv", customFieldsCsv, [
      "project_id",
      "custom_attribute_id",
      "name",
      "display_name",
      "description",
      "data_type",
      "required",
      "values",
      "values_and_ids",
    ]);
    console.log(
      "\n=== Saved custom_fields.csv with custom attributes data ==="
    );

    // --- Categories CSV ---
    const categoriesCsv: any[] = [];
    for (const cat of categoriesWithStatus) {
      const customAttrStr = (cat.customAttributes || [])
        .map((ca: any) => ca.displayName)
        .filter((n: any) => n)
        .join(";");

      categoriesCsv.push({
        project_id: projectId,
        category_id: cat.categoryId,
        category_name: cat.categoryName,
        parent_id: cat.parentId,
        status_set_id: cat.statusSetId,
        status_set_name: cat.statusSetName,
        custom_attributes: customAttrStr,
      });
    }

    saveCsv("categories.csv", categoriesCsv, [
      "project_id",
      "category_id",
      "category_name",
      "parent_id",
      "status_set_id",
      "status_set_name",
      "custom_attributes",
    ]);
    console.log("\n=== Saved categories.csv with categories data ===");

    // === 9️⃣ Create category_status_default.csv ===

    // Find IFCGlobalId custom attribute name
    let ifcGlobalIdName = "";
    for (const ca of customAttributes) {
      if ((ca.displayName || "").trim() === "IFCGlobalId") {
        ifcGlobalIdName = ca.name;
        break;
      }
    }

    // Build a mapping of status_set_name -> first status_id
    const statusSetNameToFirstStatus: Record<string, string> = {};
    for (const row of statusSetsCsv) {
      const ssName = row.status_set_name;
      const sId = row.status_id;

      // Keep the first status_id for each status_set_name
      if (ssName && sId && !statusSetNameToFirstStatus[ssName]) {
        statusSetNameToFirstStatus[ssName] = sId;
      }
    }

    // Build category_status_default.csv
    const categoryStatusDefaultCsv: any[] = [];
    for (const cat of categoriesCsv) {
      const ssName = cat.status_set_name;
      const defaultStatusId = statusSetNameToFirstStatus[ssName] || "";

      categoryStatusDefaultCsv.push({
        category_name: cat.category_name,
        category_id: cat.category_id,
        default_status_id: defaultStatusId,
        IFCGlobalID_cat_name: ifcGlobalIdName || "",
      });
    }

    // Write category_status_default.csv
    const outputDefPath = path.join(
      getOutputDir(),
      "category_status_default.csv"
    );
    // Using explicit BOM handling for Excel compatibility
    const outputDef = stringify(categoryStatusDefaultCsv, {
      header: true,
      columns: [
        "category_name",
        "category_id",
        "default_status_id",
        "IFCGlobalID_cat_name",
      ],
      bom: true,
    });
    fs.writeFileSync(outputDefPath, outputDef);

    console.log(
      `\n=== Saved category_status_default.csv with default status mappings to ${outputDefPath} ===`
    );
    console.log(decodeURIComponent(msg));

    return res.redirect(`/?msg=${msg}`);
  } catch (e: any) {
    const errMsg = encodeURIComponent(
      `Error fetching assets info: ${e.message}`
    );
    return res.redirect(`/?msg=${errMsg}`);
  }
}
