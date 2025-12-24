# Singapore Built Industry - ACC Project Initial Setup

This folder contains comprehensive hardcoded configurations for setting up a fresh Autodesk Construction Cloud (ACC) project tailored to the **Singapore construction industry context**.

## 📋 Contents

### 1. **new_status_sets.json** (10 Status Sets)

Comprehensive workflow stages covering the entire project lifecycle:

- **Design & Documentation** - Design development phases
- **Procurement & Submission** - Material procurement workflow
- **BCA Submission** - Building & Construction Authority approvals
- **Construction Progress** - On-site execution stages
- **Inspection & Testing** - Quality assurance and testing
- **Fire Safety Compliance** - SCDF fire safety submissions
- **MEP Systems** - Mechanical, Electrical & Plumbing lifecycle
- **Defects & Rectification** - Defects liability management
- **Handover & Warranty** - Project completion and handover
- **Sustainability & Green Mark** - BCA Green Mark certification

### 2. **new_custom_fields.json** (40 Custom Fields)

Extensive field library covering all project tracking needs:

**Core BIM & Identification:**

- IFCGlobalId (REQUIRED - included in every category)
- IFC_Type
- Drawing Reference
- Specification Reference

**Project Team:**

- Main Contractor, Subcontractor, Supplier, Design Consultant

**Location & Structure:**

- Location/Zone, Level/Storey, Grid Reference

**Materials & Specifications:**

- Material Specification, Fire Rating, Acoustic Rating

**Scheduling:**

- Planned Start/Completion Dates
- Actual Start/Completion Dates

**Singapore Authority Compliance:**

- BCA Submission Required/Number
- SCDF Approval Required
- PE/QP Endorsement
- Inspection Authority (BCA, SCDF, NEA, PUB, LTA, URA, etc.)

**Sustainability (Green Mark):**

- Green Mark Contribution
- Sustainability Features

**Asset Management:**

- Asset Value (SGD), Quantity, Unit of Measurement
- Manufacturer, Model Number, Serial Number
- Warranty Period/Expiry

**Maintenance & Inspection:**

- Maintenance Schedule
- Last/Next Inspection Date
- Defects Identified
- Criticality Level

### 3. **new_categories.json** (23 Categories)

Hierarchical category structure reflecting Singapore construction practices:

**ROOT Categories:**

- Architectural Works
- Structural Works
- Mechanical Systems
- Plumbing & Sanitary
- Electrical Systems
- Fire Protection Systems
- Facade & Cladding
- Lifts & Escalators
- ELV Systems
- Landscape & External Works
- Temporary Works

**Subcategories include:**

- External Walls, Doors & Windows (under Architectural)
- Foundations & Piling, Columns & Beams, Slabs & Floors (under Structural)
- ACMV Systems (under Mechanical)
- Main Switchboards, Lighting Systems (under Electrical)
- Fire Sprinkler Systems, Fire Alarm & Detection (under Fire Protection)

## 🎯 Key Features

### Singapore-Specific Compliance

✅ **BCA (Building & Construction Authority)** submission tracking  
✅ **SCDF (Singapore Civil Defence Force)** fire safety approvals  
✅ **PE/QP (Professional Engineer/Qualified Person)** endorsements  
✅ **Green Mark** sustainability certification tracking  
✅ **Statutory approvals** (TOP, CSC) in handover workflow

### Industry Best Practices

✅ **IFCGlobalId mandatory** - Ensures BIM coordination across all categories  
✅ **Trade-specific workflows** - Each category uses appropriate status set  
✅ **Comprehensive tracking** - From design through warranty period  
✅ **Multi-authority coordination** - BCA, SCDF, NEA, PUB, LTA, URA tracking

### Asset Management Ready

✅ **Financial tracking** - Asset values in SGD  
✅ **Warranty management** - Period and expiry tracking  
✅ **Maintenance scheduling** - Preventive maintenance planning  
✅ **Inspection cycles** - Last/next inspection dates  
✅ **Criticality ratings** - Risk-based asset prioritization

## 🚀 Usage Instructions

### Step 1: Create Status Sets

1. Navigate to **"Create Status Sets"** tab in ACC Asset Manager
2. Use the **"Create All Status Sets"** button
3. Reference: `new_status_sets.json`
4. All 10 status sets will be created with proper color coding

### Step 2: Create Custom Fields

1. Navigate to **"Create Custom Fields"** tab
2. Use the **"Create All Custom Fields"** button
3. Reference: `new_custom_fields.json`
4. 40 custom fields will be created with proper data types

### Step 3: Create Categories

1. Navigate to **"Create Categories"** tab
2. Load category data from `new_categories.json`
3. Use the **"Create All Categories"** button
4. Categories will be created with:
   - Proper parent-child hierarchy
   - Mapped status sets
   - Assigned custom fields (including mandatory IFCGlobalId)

### Step 4: Verify Configuration

1. Navigate to **"Config Structure"** tab
2. Click **"Load Config Structure"**
3. Verify all categories, status sets, and custom fields are properly mapped
4. Download JSON for backup/documentation

## 📊 Data Structure

### Status Set Format

```json
{
  "name": "Status Set Name",
  "status_set_description": "Description of workflow",
  "status_label": ["First Status", "Second Status", ...],
  "description": ["First description", "Second description", ...],
  "status_colors": ["adsk-color-1", "adsk-color-2", ...]
}
```

**Note:** First status in array is the default status (e.g., "Not Started", "Pending")

### Custom Field Format

```json
{
  "displayName": "Field Display Name",
  "description": "Field description",
  "enumValues": ["Option1", "Option2"],
  "requiredOnIngress": true/false,
  "maxLengthOnIngress": 100,
  "defaultValue": "Default value",
  "dataType": "text|numeric|date|boolean|select|multi_select"
}
```

### Category Format

```json
{
  "name": "Category Name",
  "description": "Category description",
  "category_parent_name": "Parent Category Name",
  "category_parent_id": 1,
  "status_set_name": "Associated Status Set",
  "custom_fields": ["Field1", "Field2", "IFCGlobalId", ...]
}
```

## 🔧 Customization Guide

### To Add New Custom Fields:

1. Add entry to `new_custom_fields.json`
2. Ensure proper `dataType` and `enumValues`
3. Set `requiredOnIngress` appropriately
4. Consider adding to relevant categories

### To Add New Categories:

1. Add entry to `new_categories.json`
2. Set appropriate `category_parent_id` (1 for ROOT categories)
3. Select suitable `status_set_name`
4. **MUST include "IFCGlobalId"** in `custom_fields` array
5. Add other relevant custom fields

### To Modify Status Sets:

1. Edit status arrays in `new_status_sets.json`
2. Ensure arrays are same length (labels, descriptions, colors)
3. First status is always the default
4. Use Autodesk color palette (adsk-\*)

## 🎨 Available Autodesk Colors

- **Neutral:** adsk-charcoal-500, adsk-charcoal-700
- **Blue:** adsk-blue-300, adsk-blue-500, adsk-blue-700
- **Green:** adsk-green-300, adsk-green-500, adsk-green-700
- **Yellow/Orange:** adsk-yellow-500, adsk-yellow-orange-500
- **Red:** adsk-red-500, adsk-red-700
- **Purple:** adsk-purple-500, adsk-purple-700
- **Others:** adsk-turquoise-500, adsk-salmon-500, adsk-pink-500, adsk-brown-500

## 📝 Singapore Construction Context

### Regulatory Bodies Covered:

- **BCA** - Building & Construction Authority (building regulations)
- **SCDF** - Singapore Civil Defence Force (fire safety)
- **NEA** - National Environment Agency (environmental compliance)
- **PUB** - Public Utilities Board (water/drainage)
- **LTA** - Land Transport Authority (transport infrastructure)
- **URA** - Urban Redevelopment Authority (planning approval)

### Key Milestones Tracked:

- Temporary Occupation Permit (TOP)
- Certificate of Statutory Completion (CSC)
- Fire Safety Certificate (FSC)
- Green Mark Certification (Provisional & Final)

### Trade Classifications:

Architectural, Structural, Civil, Mechanical, Electrical, Plumbing, Fire Protection, ACMV, ELV Systems, Facade, Landscape

## ⚠️ Important Notes

1. **IFCGlobalId is MANDATORY** in all categories for BIM coordination
2. **First status value** in each status set is the default (e.g., "Not Started")
3. **Parent category references** will be resolved during creation
4. **Status set names** must match exactly between files
5. **Custom field names** must match exactly between files
6. **Asset values** use Singapore Dollars (SGD)

## 🔄 Update Workflow

To update an existing project:

1. Backup current configuration using "Config Structure" tab
2. Modify JSON files as needed
3. Create new items (will not duplicate existing)
4. Manually map new fields to existing categories if needed

## 📚 References

- [Autodesk Construction Cloud Assets API](https://aps.autodesk.com/en/docs/acc/v1/reference/http/assets/)
- [BCA Approved Document](https://www.bca.gov.sg/)
- [SCDF Fire Safety Requirements](https://www.scdf.gov.sg/)
- [BCA Green Mark Scheme](https://www.bca.gov.sg/greenmark/)

---

**Created for:** Singapore Built Industry ACC Projects  
**Last Updated:** November 2025  
**Compatibility:** Autodesk Construction Cloud Assets API v1  
**Standards:** IFC 4.0, Singapore Building Regulations
