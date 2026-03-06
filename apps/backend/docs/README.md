# 📚 Documentation Structure

**Organized Documentation Hub**  
Last Updated: February 1, 2026

---

## 📁 Folder Organization

```
docs/
├── guides/                              # Setup & Implementation Guides
│   ├── GEMINI_AI_CHATBOT_SETUP.md      # AI Chatbot setup instructions
│   ├── AI_CHATBOT_INTEGRATION_GUIDE.md # Integration for 6 platforms
│   ├── LOAN_PRODUCTS_GUIDE.md          # Loan products system
│   ├── LOAN_PRODUCTS_DEPLOYMENT_SUMMARY.md
│   ├── UPLOAD_AND_ANALYSIS_GUIDE.md    # Data upload & analysis
│   └── EMAIL_CONFIGURATION.md          # Email setup
│
├── api/                                 # API Documentation
│   ├── API_ENDPOINTS_GUIDE.md          # All endpoints reference
│   └── api-docs.md                     # API documentation
│
├── database/                            # Database Documentation
│   └── database_architecture_guide.py  # Database architecture
│
├── sql-scripts/                         # SQL Migration Scripts
│   ├── ALTER_USER_TABLE.sql
│   ├── CHECK_COMPATIBILITY.sql
│   ├── CREATE_RELATIONSHIPS.sql
│   ├── CREATE_RISK_CLASSIFICATION_TABLES.sql
│   ├── ETL_IMPORT_PIPELINE.sql
│   ├── INSERT_SAMPLE_USERS_PER_ROLE.sql
│   ├── SAMPLE_DATA_INSERTION.sql
│   ├── SAMPLE_DATA_INSERTION_FIXED.sql
│   ├── SQL_SCHEMA_ENHANCEMENTS.sql
│   ├── SQLQuery1.sql
│   ├── SQLQuery2.sql
│   ├── SQLQuery3.sql
│   └── script.sql
│
└── README.md                            # This file

```

---

## 🗂️ Quick Navigation

### 📖 Setup & Implementation Guides (`guides/`)
Start here for setup and implementation:

| Guide | Purpose | Read Time |
|-------|---------|-----------|
| **GEMINI_AI_CHATBOT_SETUP.md** | Complete AI chatbot setup | 20-30 min |
| **AI_CHATBOT_INTEGRATION_GUIDE.md** | Integration (6 platforms) | 25-30 min |
| **LOAN_PRODUCTS_GUIDE.md** | Loan products system | 15-20 min |
| **UPLOAD_AND_ANALYSIS_GUIDE.md** | Data upload & analysis | 15-20 min |
| **EMAIL_CONFIGURATION.md** | Email setup | 10 min |
| **LOAN_PRODUCTS_DEPLOYMENT_SUMMARY.md** | Deployment summary | 10 min |

### 🔌 API Documentation (`api/`)
API reference and documentation:

| Document | Purpose |
|----------|---------|
| **API_ENDPOINTS_GUIDE.md** | Complete endpoint reference |
| **api-docs.md** | API documentation |

### 🗄️ Database (`database/`)
Database architecture and design:

| Document | Purpose |
|----------|---------|
| **database_architecture_guide.py** | Database architecture |

### 🛠️ SQL Scripts (`sql-scripts/`)
Database migration and setup scripts:

| Script | Purpose |
|--------|---------|
| **CREATE_RELATIONSHIPS.sql** | Foreign key relationships |
| **CREATE_RISK_CLASSIFICATION_TABLES.sql** | Risk classification tables |
| **INSERT_SAMPLE_USERS_PER_ROLE.sql** | Sample users by role |
| **ETL_IMPORT_PIPELINE.sql** | ETL pipeline |
| **SQL_SCHEMA_ENHANCEMENTS.sql** | Schema enhancements |
| **SAMPLE_DATA_INSERTION.sql** | Sample data |
| **CHECK_COMPATIBILITY.sql** | Compatibility checks |
| **ALTER_USER_TABLE.sql** | User table modifications |
| **Other scripts** | Additional setup & testing |

---

## 🚀 Getting Started

### 1. **First Time Setup**
Start with: `guides/GEMINI_AI_CHATBOT_SETUP.md`

### 2. **API Integration**
Follow: `guides/AI_CHATBOT_INTEGRATION_GUIDE.md`

### 3. **Database Setup**
Use scripts in: `sql-scripts/`

### 4. **API Reference**
Check: `api/API_ENDPOINTS_GUIDE.md`

### 5. **Database Architecture**
Review: `database/database_architecture_guide.py`

---

## 📊 File Statistics

| Folder | Files | Type | Purpose |
|--------|-------|------|---------|
| **guides/** | 6 | Markdown | Implementation guides |
| **api/** | 2 | Markdown | API documentation |
| **database/** | 1 | Python | Database design |
| **sql-scripts/** | 13 | SQL | Database scripts |

**Total**: 22 organized files

---

## 🎯 By Use Case

### **Setting Up AI Chatbot**
1. `guides/GEMINI_AI_CHATBOT_SETUP.md` - Full setup
2. `guides/AI_CHATBOT_INTEGRATION_GUIDE.md` - Integration
3. `api/API_ENDPOINTS_GUIDE.md` - API reference

### **Setting Up Loan Products**
1. `guides/LOAN_PRODUCTS_GUIDE.md` - Product system
2. `guides/LOAN_PRODUCTS_DEPLOYMENT_SUMMARY.md` - Deployment
3. `sql-scripts/` - Database scripts

### **Setting Up Database**
1. `database/database_architecture_guide.py` - Architecture
2. `sql-scripts/` - Migration scripts
3. `api/API_ENDPOINTS_GUIDE.md` - Endpoints

### **Data Upload & Analysis**
1. `guides/UPLOAD_AND_ANALYSIS_GUIDE.md` - Upload guide
2. `sql-scripts/ETL_IMPORT_PIPELINE.sql` - ETL pipeline
3. `api/API_ENDPOINTS_GUIDE.md` - Analysis endpoints

### **Email Configuration**
1. `guides/EMAIL_CONFIGURATION.md` - Setup guide

---

## 🔍 Finding Documents

### By Topic

**AI & Chatbot**
- `guides/GEMINI_AI_CHATBOT_SETUP.md`
- `guides/AI_CHATBOT_INTEGRATION_GUIDE.md`
- `api/API_ENDPOINTS_GUIDE.md` (AI endpoints)

**Loan Products**
- `guides/LOAN_PRODUCTS_GUIDE.md`
- `guides/LOAN_PRODUCTS_DEPLOYMENT_SUMMARY.md`
- `sql-scripts/` (Product tables)

**Risk Management**
- `sql-scripts/CREATE_RISK_CLASSIFICATION_TABLES.sql`
- `guides/UPLOAD_AND_ANALYSIS_GUIDE.md`

**API**
- `api/API_ENDPOINTS_GUIDE.md`
- `api/api-docs.md`

**Database**
- `database/database_architecture_guide.py`
- `sql-scripts/` (All migration scripts)

**Configuration**
- `guides/EMAIL_CONFIGURATION.md`
- `guides/GEMINI_AI_CHATBOT_SETUP.md` (Gemini config)

---

## 📋 SQL Scripts by Purpose

### Table Creation
- `CREATE_RELATIONSHIPS.sql` - Foreign keys
- `CREATE_RISK_CLASSIFICATION_TABLES.sql` - Risk tables
- `SQL_SCHEMA_ENHANCEMENTS.sql` - Schema changes

### Data Insertion
- `INSERT_SAMPLE_USERS_PER_ROLE.sql` - Users by role
- `SAMPLE_DATA_INSERTION.sql` - Sample data
- `SAMPLE_DATA_INSERTION_FIXED.sql` - Fixed sample data
- `ETL_IMPORT_PIPELINE.sql` - ETL data

### Schema Modifications
- `ALTER_USER_TABLE.sql` - User table changes

### Verification & Testing
- `CHECK_COMPATIBILITY.sql` - Compatibility checks
- `SQLQuery1.sql` - Test query 1
- `SQLQuery2.sql` - Test query 2
- `SQLQuery3.sql` - Test query 3
- `script.sql` - General script

---

## 🎓 Learning Path

### Beginner (New to Project)
1. Read: `guides/GEMINI_AI_CHATBOT_SETUP.md`
2. Read: `guides/LOAN_PRODUCTS_GUIDE.md`
3. Review: `api/API_ENDPOINTS_GUIDE.md`

### Intermediate (Want to Integrate)
1. Read: `guides/AI_CHATBOT_INTEGRATION_GUIDE.md`
2. Review: `api/api-docs.md`
3. Study: `database/database_architecture_guide.py`

### Advanced (Architecture & Design)
1. Study: `database/database_architecture_guide.py`
2. Review: `sql-scripts/` (all scripts)
3. Analyze: `api/API_ENDPOINTS_GUIDE.md`

---

## ✅ Checklist

### Initial Setup
- [ ] Read setup guides
- [ ] Review API documentation
- [ ] Understand database schema
- [ ] Run SQL scripts

### Integration
- [ ] Choose platform (Flutter/React/etc)
- [ ] Follow integration guide
- [ ] Review API endpoints
- [ ] Test API calls

### Deployment
- [ ] Review SQL scripts
- [ ] Setup database
- [ ] Configure email
- [ ] Deploy API
- [ ] Test endpoints

---

## 📞 Need Help?

| Need | Location |
|------|----------|
| **Setup AI Chatbot** | `guides/GEMINI_AI_CHATBOT_SETUP.md` |
| **Integrate with App** | `guides/AI_CHATBOT_INTEGRATION_GUIDE.md` |
| **Setup Loan Products** | `guides/LOAN_PRODUCTS_GUIDE.md` |
| **Upload Data** | `guides/UPLOAD_AND_ANALYSIS_GUIDE.md` |
| **Configure Email** | `guides/EMAIL_CONFIGURATION.md` |
| **View API** | `api/API_ENDPOINTS_GUIDE.md` |
| **Database Design** | `database/database_architecture_guide.py` |
| **Run SQL** | `sql-scripts/` |

---

## 🔄 File Updates

All files are organized as of **February 1, 2026**

**Last organized**: 2026-02-01  
**Total files**: 22  
**Total guides**: 6  
**Total scripts**: 13  

---

**Navigation**: Quick reference for all documentation  
**Status**: ✅ Fully organized  
**Ready to use**: ✅ Yes
