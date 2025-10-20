# ⚖️ Indian Court Case Data Fetcher & Automation Tool

A comprehensive Python-based web automation tool for fetching case details and daily cause lists from Indian court websites (eCourts and Delhi District Courts). Built with Streamlit for an intuitive user interface and Selenium for robust web scraping.

---

## 🎯 Project Overview

This application automates the tedious process of manually searching for case information on court websites. It provides a streamlined interface to:
- Search for case status and details across Indian courts
- Fetch daily cause lists from Delhi District Courts
- Maintain a searchable history of all queries
- Export data in multiple formats (CSV, PDF)

---

## ✨ Key Features

### 1. **Case Status Search** 🔍
- Automated form filling with intelligent dropdown matching
- Support for multiple case types across different courts
- Smart element detection with fallback mechanisms
- Extracts comprehensive case information:
  - Party names
  - Filing dates
  - Case status
  - Complete case details

### 2. **Daily Cause List Fetcher** 📋
- Direct integration with Delhi District Courts website
- Support for all major court complexes:
  - Patiala House, Tis Hazari, Karkardooma, Rohini, Dwarka, Saket, Rouse Avenue
- Civil and Criminal list support
- Section-wise data organization
- Automatic calendar table filtering

### 3. **Query History Management** 🗂️
- SQLite database for persistent storage
- Separate tracking for case status and cause list queries
- Timestamp and parameter logging
- Quick reference and audit trail

### 4. **Export Options** 📥
- **CSV Export**: Excel-compatible format with proper encoding
- **PDF Export**: Professional reports with:
  - Custom layouts and styling
  - Smart column width allocation
  - Text wrapping for long content
  - Section-wise organization

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | Streamlit - Interactive web interface |
| **Web Automation** | Selenium WebDriver - Browser automation |
| **Web Scraping** | BeautifulSoup4 - HTML parsing |
| **Database** | SQLite - Query history storage |
| **Data Processing** | Pandas - Data manipulation |
| **PDF Generation** | ReportLab - Professional document creation |
| **Language** | Python 3.8+ |

---

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- Chrome browser installed
- ChromeDriver (automatically managed by Selenium)

### Setup Steps

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/court-case-fetcher.git
cd court-case-fetcher
```

2. **Install dependencies**
```bash
pip install streamlit selenium beautifulsoup4 pandas reportlab
```

3. **Run the application**
```bash
streamlit run mvp_court_case.py
```

4. **Access the application**
- Open your browser and navigate to `http://localhost:8501`

---

## 📋 Requirements

```txt
streamlit>=1.28.0
selenium>=4.15.0
beautifulsoup4>=4.12.0
pandas>=2.0.0
reportlab>=4.0.0
```

---

## 🚀 Usage Guide

### Fetching Case Details

1. **Navigate to "Fetch New Case Data" tab**
2. **Enter court information:**
   - State name (e.g., Delhi)
   - District name (e.g., South West)
   - Court complex (e.g., Dwarka Courts)
3. **Enter case details:**
   - Select case type from dropdown
   - Enter case number
   - Select year
4. **Click "Fetch Case Details"**
5. **Solve CAPTCHA** in the opened browser
6. **View results** and download as CSV/PDF

### Fetching Cause Lists

1. **Navigate to "Fetch Cause List" tab**
2. **Select parameters:**
   - Court complex
   - Civil or Criminal list
   - Date from calendar
   - (Optional) Specific court/judge
3. **Click "Fetch Cause List"**
4. **Complete form** and solve CAPTCHA in browser
5. **View section-wise breakdown** and download

### Viewing History

1. **Navigate to "View History" tab**
2. **Browse two types of history:**
   - Case Status History
   - Cause List History
3. **Click "Refresh"** to update

---

## 🎨 Features Highlights

### Intelligent Automation
- **Smart Matching**: Fuzzy matching for dropdown options
- **Error Handling**: Graceful degradation with user guidance
- **Modal Detection**: Automatic dismissal of popup dialogs
- **Multiple Selectors**: Fallback strategies for element detection

### User-Friendly Interface
- **Three-Tab Layout**: Organized and intuitive
- **Visual Feedback**: Progress bars and status messages
- **Form Validation**: Real-time error checking
- **Responsive Design**: Works on different screen sizes

### Professional Exports
- **PDF Reports**: Custom styling with proper formatting
- **CSV Files**: Excel-compatible with proper encoding
- **Smart Column Widths**: Optimal space allocation
- **Text Wrapping**: Handles long content gracefully

---

## 🔧 Technical Implementation

### Web Automation Strategy
```python
- WebDriver initialization with Chrome
- Explicit waits for dynamic content
- JavaScript execution for problematic elements
- BeautifulSoup for HTML parsing
```

### Database Schema
```sql
-- Case Status Queries
queries (
    id, case_type, case_number, case_year,
    parties, filing_date, case_status,
    raw_response_html, timestamp
)

-- Cause List Queries
cause_lists (
    id, court_complex, court_number,
    list_date, list_type, total_cases, timestamp
)
```

### Error Handling
- Comprehensive try-catch blocks
- User-friendly error messages
- Automatic fallback mechanisms
- Debug information for troubleshooting

---

## 🎯 Use Cases

### For Legal Professionals
- Quick case status verification
- Daily cause list monitoring
- Case documentation and record keeping
- Client update automation

### For Litigants
- Self-service case tracking
- Hearing date notifications
- Case progress monitoring
- Document generation

### For Researchers
- Court data collection
- Case trend analysis
- Historical record compilation
- Statistical research

---

## 🔒 Privacy & Security

- **Local Storage**: All data stored locally in SQLite
- **No Cloud Dependency**: Complete privacy
- **Manual CAPTCHA**: Respects court website security
- **Ethical Scraping**: Follows robots.txt guidelines

---

## 🚧 Limitations

- **CAPTCHA**: Requires manual solving (by design, for security)
- **Website Changes**: May need updates if court websites change
- **Delhi Focus**: Cause list feature primarily for Delhi courts
- **Browser Required**: Needs Chrome browser installed

---

## 🔮 Future Enhancements

- [ ] Multi-state support for cause lists
- [ ] Email/SMS notifications for case updates
- [ ] Advanced search and filtering
- [ ] Bulk case processing
- [ ] Dashboard with analytics
- [ ] Mobile app version
- [ ] RESTful API for third-party integration
- [ ] OCR for document processing

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## ⚠️ Disclaimer

This tool is for educational and personal use only. Always respect court website terms of service and robots.txt files. The author is not responsible for any misuse of this tool. Use responsibly and ethically.

---

## 🙏 Acknowledgments

- eCourts India for providing public access to case information
- Delhi District Courts for the cause list portal
- Streamlit community for the amazing framework
- Selenium project for web automation capabilities

---

**⭐ Star this repository if you find it helpful!**

**Made with ❤️ for the legal community**
