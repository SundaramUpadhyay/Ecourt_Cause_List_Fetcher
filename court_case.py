import streamlit as st
import sqlite3
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT

DB_FILE = "case_data.db"

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Case status queries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_type TEXT NOT NULL,
        case_number TEXT NOT NULL,
        case_year INTEGER NOT NULL,
        parties TEXT,
        filing_date TEXT,
        case_status TEXT,
        raw_response_html TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Cause list queries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cause_lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        court_complex TEXT NOT NULL,
        court_number TEXT,
        list_date TEXT NOT NULL,
        list_type TEXT NOT NULL,
        total_cases INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

def store_query_result(case_type, number, year, parsed_data, raw_html):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO queries 
           (case_type, case_number, case_year, parties, filing_date, case_status, raw_response_html) 
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (case_type, number, year, 
         parsed_data.get('parties'), parsed_data.get('filing_date'), parsed_data.get('status'), 
         raw_html)
    )
    conn.commit()
    conn.close()

def store_cause_list_result(court_complex, court_number, list_date, list_type, total_cases):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO cause_lists 
           (court_complex, court_number, list_date, list_type, total_cases) 
           VALUES (?, ?, ?, ?, ?)""",
        (court_complex, court_number, list_date, list_type, total_cases)
    )
    conn.commit()
    conn.close()

def generate_case_details_pdf(case_data, case_type, case_number, case_year):
    """Generate PDF for case details"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Add title
    title = Paragraph(f"<b>Case Details Report</b>", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Add case information
    case_info_data = [
        ['Case Type:', case_type],
        ['Case Number:', case_number],
        ['Case Year:', str(case_year)],
        ['Generated On:', pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')]
    ]
    
    case_info_table = Table(case_info_data, colWidths=[2*inch, 4*inch])
    case_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    elements.append(case_info_table)
    elements.append(Spacer(1, 20))
    
    # Add fetched data
    heading = Paragraph("<b>Fetched Information</b>", heading_style)
    elements.append(heading)
    
    fetched_data = []
    for key, value in case_data.items():
        fetched_data.append([key.replace('_', ' ').title() + ':', str(value)])
    
    fetched_table = Table(fetched_data, colWidths=[2*inch, 4*inch])
    fetched_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    
    elements.append(fetched_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_cause_list_pdf(df, court_complex, date, list_type):
    """Generate PDF for cause list with proper text wrapping"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20,
                           topMargin=30, bottomMargin=18)
    
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=15,
        alignment=TA_CENTER
    )
    
    # Cell text style for wrapping
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        alignment=TA_LEFT,
        wordWrap='CJK'
    )
    
    header_cell_style = ParagraphStyle(
        'HeaderCellStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.whitesmoke,
        fontName='Helvetica-Bold',
        wordWrap='CJK'
    )
    
    # Add title
    title = Paragraph(f"<b>{list_type} Cause List Report</b>", title_style)
    elements.append(title)
    
    # Add header info
    header_data = [
        ['Court Complex:', court_complex],
        ['Date:', date],
        ['List Type:', list_type],
        ['Total Cases:', str(len(df))],
        ['Generated On:', pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')]
    ]
    
    header_table = Table(header_data, colWidths=[1.5*inch, 4.5*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 15))
    
    # Define custom column widths based on typical cause list structure
    # Assuming columns: Serial Number, Case Type/Number/Year, Party Name, Advocate
    def get_column_widths(columns):
        """Smart column width allocation based on column names"""
        total_width = 7.5 * inch  # Total available width on A4
        widths = []
        
        for col in columns:
            col_lower = str(col).lower()
            if 'serial' in col_lower or 'sr' in col_lower or 'no' in col_lower:
                widths.append(0.5 * inch)  # Serial number - narrow
            elif 'case' in col_lower or 'type' in col_lower or 'number' in col_lower:
                widths.append(1.5 * inch)  # Case details - medium
            elif 'party' in col_lower or 'name' in col_lower:
                widths.append(3.0 * inch)  # Party names - widest
            elif 'advocate' in col_lower or 'lawyer' in col_lower:
                widths.append(1.5 * inch)  # Advocate - medium
            else:
                widths.append(1.0 * inch)  # Default
        
        # Normalize to fit total width
        current_total = sum(widths)
        if current_total > total_width:
            scale_factor = total_width / current_total
            widths = [w * scale_factor for w in widths]
        
        return widths
    
    # Group by section if available
    if 'Section' in df.columns:
        for section in df['Section'].unique():
            section_df = df[df['Section'] == section].copy()
            
            # Section heading
            section_heading = Paragraph(f"<b>{section} ({len(section_df)} cases)</b>", 
                                       styles['Heading3'])
            elements.append(section_heading)
            elements.append(Spacer(1, 8))
            
            # Prepare table data with Paragraphs for text wrapping
            display_df = section_df.drop('Section', axis=1)
            
            # Create header row with Paragraphs
            header_row = [Paragraph(f"<b>{col}</b>", header_cell_style) for col in display_df.columns]
            table_data = [header_row]
            
            # Create data rows with Paragraphs
            for _, row in display_df.iterrows():
                row_data = []
                for val in row:
                    # Convert to string and wrap in Paragraph for automatic text wrapping
                    text = str(val) if pd.notna(val) else ''
                    row_data.append(Paragraph(text, cell_style))
                table_data.append(row_data)
            
            # Get smart column widths
            col_widths = get_column_widths(display_df.columns)
            
            # Create table with proper wrapping
            cause_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            cause_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Serial number centered
                ('ALIGN', (1, 1), (-1, -1), 'LEFT'),   # Rest left-aligned
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ]))
            
            elements.append(cause_table)
            elements.append(Spacer(1, 12))
            
            # Add page break between sections (except last)
            if section != df['Section'].unique()[-1]:
                elements.append(PageBreak())
    else:
        # No sections, just display all data
        # Create header row with Paragraphs
        header_row = [Paragraph(f"<b>{col}</b>", header_cell_style) for col in df.columns]
        table_data = [header_row]
        
        # Create data rows with Paragraphs
        for _, row in df.iterrows():
            row_data = []
            for val in row:
                text = str(val) if pd.notna(val) else ''
                row_data.append(Paragraph(text, cell_style))
            table_data.append(row_data)
        
        # Get smart column widths
        col_widths = get_column_widths(df.columns)
        
        cause_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        cause_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        
        elements.append(cause_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def view_all_data():
    conn = sqlite3.connect(DB_FILE)
    
    # Get case status queries
    case_df = pd.read_sql_query(
        "SELECT id, timestamp, case_type, case_number, case_year, case_status FROM queries ORDER BY timestamp DESC", 
        conn
    )
    case_df['query_type'] = 'Case Status'
    
    # Get cause list queries
    cause_list_df = pd.read_sql_query(
        "SELECT id, timestamp, court_complex, list_date, list_type, total_cases FROM cause_lists ORDER BY timestamp DESC", 
        conn
    )
    cause_list_df['query_type'] = 'Cause List'
    
    conn.close()
    
    return case_df, cause_list_df

def fetch_case_data(case_type, case_number, year, state_name, district_name, court_complex_name):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        return None, f"WebDriver Error: {e}. Ensure chromedriver is in your PATH."

    try:
        driver.get("https://services.ecourts.gov.in/ecourtindia_v6/")
        
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "leftPaneMenuCS"))).click()

        # Wait for state dropdown to be present
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "sess_state_code")))
        state_dropdown = Select(driver.find_element(By.ID, "sess_state_code"))
        
        # Debug: Print available states
        available_states = [option.text for option in state_dropdown.options]
        st.info(f"Available states: {', '.join(available_states[:5])}...")
        
        # Try to select state (with error handling)
        state_selected = False
        try:
            state_dropdown.select_by_visible_text(state_name)
            state_selected = True
        except:
            # Try partial match
            for option in state_dropdown.options:
                if state_name.lower() in option.text.lower():
                    option.click()
                    state_selected = True
                    break
        
        if not state_selected:
            return None, f"Could not find state '{state_name}'. Available states: {', '.join(available_states)}"
        
        # Wait for district dropdown to load
        time.sleep(2)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "sess_dist_code")))
        district_dropdown = Select(driver.find_element(By.ID, "sess_dist_code"))
        
        # Debug: Print available districts
        available_districts = [option.text for option in district_dropdown.options if option.text.strip()]
        st.info(f"Available districts: {', '.join(available_districts)}")
        
        # Try to select district (with error handling)
        district_selected = False
        try:
            district_dropdown.select_by_visible_text(district_name)
            district_selected = True
        except:
            # Try partial match
            for option in district_dropdown.options:
                if district_name.lower() in option.text.lower():
                    option.click()
                    district_selected = True
                    break

        if not district_selected:
            return None, f"Could not find district '{district_name}'. Available districts: {', '.join(available_districts)}"

        # Wait for court complex dropdown to load
        time.sleep(2)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "court_complex_code")))
        court_complex_dropdown = Select(driver.find_element(By.ID, "court_complex_code"))
        
        # Debug: Print available court complexes
        available_courts = [option.text for option in court_complex_dropdown.options if option.text.strip()]
        st.info(f"Available court complexes: {', '.join(available_courts)}")
        
        # Try to select court complex (with error handling)
        court_selected = False
        try:
            court_complex_dropdown.select_by_visible_text(court_complex_name)
            court_selected = True
        except:
            # Try partial match
            for option in court_complex_dropdown.options:
                if court_complex_name.lower() in option.text.lower():
                    option.click()
                    court_selected = True
                    break
        
        if not court_selected:
            return None, f"Could not find court complex '{court_complex_name}'. Available courts: {', '.join(available_courts)}"
        
        # Wait a moment for any validation
        time.sleep(1)
        
        # Check for and dismiss any modal dialogs
        try:
            # Look for validation error modal
            modal = driver.find_element(By.ID, "validateError")
            if modal.is_displayed():
                st.warning("Validation error modal detected. Attempting to close...")
                # Try to find and click close button
                try:
                    close_button = driver.find_element(By.CSS_SELECTOR, "#validateError .btn-close, #validateError button.close, #validateError .modal-footer button")
                    close_button.click()
                    time.sleep(1)
                except:
                    # If can't find close button, try pressing ESC
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(1)
        except:
            # No modal found, continue
            pass
        
        # Use JavaScript click to avoid interception
        case_number_tab = driver.find_element(By.ID, "casenumber-tabMenu")
        driver.execute_script("arguments[0].click();", case_number_tab)
        
        time.sleep(2)  # Increased wait time for tab content to load
        
        # Get case type dropdown and show available options
        case_type_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "case_type"))
        )
        case_type_dropdown = Select(case_type_element)
        available_case_types = [option.text for option in case_type_dropdown.options if option.text.strip()]
        st.info(f"Available case types: {', '.join(available_case_types[:10])}... ({len(available_case_types)} total)")
        
        # Try to select case type (with error handling)
        case_type_selected = False
        try:
            # First try exact match
            case_type_dropdown.select_by_visible_text(case_type)
            case_type_selected = True
            st.success(f"Selected case type: {case_type}")
        except:
            # Try partial match - match the beginning part before any dash or description
            case_type_clean = case_type.split(' - ')[0].strip() if ' - ' in case_type else case_type.strip()
            
            for option in case_type_dropdown.options:
                option_text = option.text.strip()
                option_clean = option_text.split(' - ')[0].strip() if ' - ' in option_text else option_text
                
                # Try to match the main part (before the dash)
                if (option_text.lower() == case_type.lower() or 
                    option_clean.lower() == case_type_clean.lower() or
                    case_type.lower() in option_text.lower() or
                    option_text.lower().startswith(case_type.lower())):
                    option.click()
                    case_type_selected = True
                    st.success(f"Matched case type: {option_text}")
                    break
        
        if not case_type_selected:
            return None, f"Could not find case type '{case_type}'. Available case types: {', '.join(available_case_types)}"
        
        # Wait a moment for the form to update after case type selection
        time.sleep(1)
        
        # Enter case number
        try:
            case_no_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "search_case_no"))
            )
            case_no_input.clear()
            case_no_input.send_keys(case_number)
            st.success(f"Entered case number: {case_number}")
        except Exception as e:
            return None, f"Could not find case number field: {e}"
        
        # Wait for year dropdown to be present and get available options
        try:
            year_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "search_case_year"))
            )
            year_dropdown = Select(year_element)
            available_years = [option.text for option in year_dropdown.options if option.text.strip()]
            st.info(f"Available years: {', '.join(available_years[:20])}...")
            
            # Try to select year
            try:
                year_dropdown.select_by_visible_text(str(year))
                st.success(f"Selected year: {year}")
            except:
                return None, f"Could not find year '{year}'. Available years: {', '.join(available_years)}"
        except Exception as e:
            # Year dropdown might not exist for this case type, try alternative selectors
            st.warning(f"Standard year dropdown not found. Trying to locate year field...")
            
            # Debug: Show all select and input elements on the page
            try:
                all_selects = driver.find_elements(By.TAG_NAME, "select")
                select_info = [f"{sel.get_attribute('id') or sel.get_attribute('name') or 'unnamed'}" for sel in all_selects if sel.is_displayed()]
                st.info(f"Found {len(select_info)} visible select elements: {', '.join(select_info[:10])}")
                
                all_inputs = driver.find_elements(By.TAG_NAME, "input")
                input_info = [f"{inp.get_attribute('id') or inp.get_attribute('name') or inp.get_attribute('type')}" for inp in all_inputs if inp.is_displayed()]
                st.info(f"Found {len(input_info)} visible input elements: {', '.join(input_info[:10])}")
            except:
                pass
            
            # Try to find any year-related input field
            year_set = False
            try:
                # Try multiple possible year field IDs/names
                possible_year_fields = ['rgyear', 'search_case_year', 'case_year', 'year']
                
                for field_id in possible_year_fields:
                    try:
                        year_input = driver.find_element(By.ID, field_id)
                        st.info(f"Found year field with ID: {field_id}")
                        
                        # Try multiple methods to set the value
                        try:
                            # Method 1: Regular send_keys
                            if year_input.is_displayed() and year_input.is_enabled():
                                year_input.clear()
                                year_input.send_keys(str(year))
                                year_set = True
                                st.success(f"Entered year using send_keys: {year}")
                                break
                        except:
                            pass
                        
                        try:
                            # Method 2: JavaScript
                            driver.execute_script(f"arguments[0].value = '{year}';", year_input)
                            # Trigger change event
                            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", year_input)
                            year_set = True
                            st.success(f"Entered year using JavaScript: {year}")
                            break
                        except:
                            pass
                    except:
                        continue
                
                if not year_set:
                    st.warning(f"⚠️ Could not automatically set year value. Please enter **{year}** manually in the 'Registration Year' field in the browser.")
            except Exception as ex:
                st.warning(f"Year field handling issue: {ex}. Continuing anyway...")

        st.info("🌐 Browser is open. Please complete the following steps:")
        st.markdown("""
        1. **Check all fields** are filled correctly (especially the year if there was a warning above)
        2. **Solve the CAPTCHA** 
        3. **Click the 'Go' button**
        4. Wait for the script to automatically parse the results
        """)
        st.warning("⏳ After you click 'Go', the script will take over and parse the results.")
        
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.ID, "case_no_res"))
        )

        raw_html = driver.page_source
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        parties_element = soup.select_one(".petitioner_advocate_tr td:nth-of-type(2)")
        
        filing_date_label = soup.find("td", string="Filing Date:")
        filing_date_element = filing_date_label.find_next_sibling("td") if filing_date_label else None

        status_label = soup.find("td", string="Case Status:")
        status_element = status_label.find_next_sibling("td") if status_label else None

        parties = parties_element.text.strip() if parties_element else "Not Found"
        filing_date = filing_date_element.text.strip() if filing_date_element else "Not Found"
        status = status_element.text.strip() if status_element else "Not Found"

        parsed_data = {"parties": parties, "filing_date": filing_date, "status": status}
        return parsed_data, raw_html

    except Exception as e:
        return None, f"An error occurred during scraping: {e}"
    finally:
        driver.quit()

def fetch_cause_list_delhi(court_complex, court_number, cause_list_date, list_type):
    """
    Fetch cause list from Delhi District Courts website
    court_complex: Name of the court complex
    court_number: Specific court/judge
    cause_list_date: Date in YYYY-MM-DD format
    list_type: 'Civil' or 'Criminal'
    """
    try:
        options = webdriver.ChromeOptions()
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()
        
        # Go directly to Delhi courts cause list page
        driver.get("https://newdelhi.dcourts.gov.in/cause-list-%E2%81%84-daily-board/")
        
        st.info("🌐 Delhi Courts Cause List page opened")
        
        time.sleep(3)
        
        # Step 1: Select "Court Complex" radio button
        try:
            radio_buttons = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for radio in radio_buttons:
                label_text = ""
                try:
                    # Try to find associated label
                    radio_id = radio.get_attribute("id")
                    if radio_id:
                        label = driver.find_element(By.CSS_SELECTOR, f"label[for='{radio_id}']")
                        label_text = label.text.strip()
                except:
                    pass
                
                # Look for "Court Complex" radio button
                if "court complex" in label_text.lower() or radio.get_attribute("value") == "court_complex":
                    driver.execute_script("arguments[0].click();", radio)
                    st.success("✅ Selected 'Court Complex' radio button")
                    time.sleep(1)
                    break
        except Exception as e:
            st.warning(f"Could not find Court Complex radio button: {e}")
        
        # Step 2: Select Court Complex from dropdown
        try:
            # Wait for court complex dropdown to appear
            time.sleep(2)
            court_complex_select = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "select[name*='complex'], select[id*='complex'], select"))
            )
            
            court_dropdown = Select(court_complex_select)
            available_courts = [option.text for option in court_dropdown.options if option.text.strip()]
            st.info(f"Available court complexes: {', '.join(available_courts)}")
            
            # Try to select the court complex
            court_selected = False
            try:
                court_dropdown.select_by_visible_text(court_complex)
                court_selected = True
                st.success(f"✅ Selected: {court_complex}")
            except:
                # Try partial match
                for option in court_dropdown.options:
                    if court_complex.lower() in option.text.lower():
                        option.click()
                        court_selected = True
                        st.success(f"✅ Matched: {option.text}")
                        break
            
            if not court_selected:
                st.warning(f"⚠️ Could not auto-select '{court_complex}'. Please select manually.")
        except Exception as e:
            st.warning(f"Court complex selection issue: {e}")
        
        time.sleep(2)
        
        # Step 3: Select Court Number from dropdown
        try:
            time.sleep(2)  # Wait for court dropdown to populate
            
            # Try multiple selectors for court dropdown
            court_num_dropdown = None
            for selector in ["select[id*='court']", "select[name*='court']", "select.form-control", "select"]:
                try:
                    selects = driver.find_elements(By.CSS_SELECTOR, selector)
                    for select_elem in selects:
                        # Check if this select has court-related options
                        select_obj = Select(select_elem)
                        options = [opt.text for opt in select_obj.options if opt.text.strip()]
                        # Look for judge names or court numbers in options
                        if any(any(keyword in opt.lower() for keyword in ['judge', 'court', 'ms.', 'mr.', 'sh.', 'smt.']) for opt in options):
                            court_num_dropdown = select_obj
                            st.info(f"Found court dropdown with {len(options)} courts")
                            st.info(f"Available courts: {', '.join(options[:3])}...")
                            break
                    if court_num_dropdown:
                        break
                except:
                    continue
            
            if court_num_dropdown:
                # Try to select court number
                if court_number:
                    selected = False
                    try:
                        court_num_dropdown.select_by_visible_text(court_number)
                        st.success(f"✅ Selected court: {court_number}")
                        selected = True
                    except:
                        # Try partial match
                        for option in court_num_dropdown.options:
                            option_text = option.text.strip()
                            if option_text and court_number.lower() in option_text.lower():
                                driver.execute_script("arguments[0].selected = true;", option)
                                driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", option.parent)
                                st.success(f"✅ Matched court: {option_text}")
                                selected = True
                                break
                    
                    if not selected:
                        st.warning(f"⚠️ Could not auto-select court '{court_number}'. Please select manually.")
                else:
                    st.info("ℹ️ No court specified. Please select court manually from dropdown.")
            else:
                st.warning("⚠️ Could not find court dropdown. Please select court manually.")
        except Exception as e:
            st.warning(f"Court number selection issue: {e}. Please select manually.")
        
        # Step 4: Set the date
        try:
            time.sleep(1)
            
            # Try multiple methods to set date
            date_set = False
            
            # Method 1: Find date input by common attributes
            try:
                # Try multiple selectors
                date_selectors = [
                    "input[type='date']",
                    "input[id*='date']",
                    "input[name*='date']",
                    "input[placeholder*='date']",
                    "input.form-control[type='date']"
                ]
                
                for selector in date_selectors:
                    date_inputs = driver.find_elements(By.CSS_SELECTOR, selector)
                    for date_input in date_inputs:
                        if date_input.is_displayed() and date_input.is_enabled():
                            try:
                                # Click the input first
                                driver.execute_script("arguments[0].focus();", date_input)
                                time.sleep(0.5)
                                
                                # Try different date formats
                                date_formats_to_try = [
                                    cause_list_date,  # DD/MM/YYYY (primary format)
                                    cause_list_date.replace('/', '-'),  # DD-MM-YYYY
                                ]
                                
                                for date_format in date_formats_to_try:
                                    try:
                                        # Clear and set value using JavaScript
                                        driver.execute_script("arguments[0].value = '';", date_input)
                                        driver.execute_script(f"arguments[0].value = '{date_format}';", date_input)
                                        
                                        # Trigger all possible events
                                        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", date_input)
                                        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", date_input)
                                        driver.execute_script("arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));", date_input)
                                        
                                        time.sleep(0.3)
                                        
                                        # Verify the value was set
                                        current_value = date_input.get_attribute('value')
                                        if current_value and len(current_value) >= 8:  # Date was set
                                            st.success(f"✅ Set date to: {date_format}")
                                            date_set = True
                                            break
                                    except:
                                        continue
                                
                                if date_set:
                                    break
                            except:
                                continue
                    if date_set:
                        break
            except:
                pass
            
            if not date_set:
                st.warning(f"⚠️ Could not automatically set date to {cause_list_date}. Please select date manually from calendar.")
        except Exception as e:
            st.warning(f"Date setting issue: {e}. Please set date manually.")
        
        time.sleep(1)
        
        # Step 5: Select Civil/Criminal radio button
        try:
            radio_selected = False
            
            # Try multiple methods to find and click radio button
            # Method 1: By value attribute
            radio_buttons = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for radio in radio_buttons:
                try:
                    radio_value = radio.get_attribute("value")
                    radio_id = radio.get_attribute("id")
                    
                    # Check if this is the Civil/Criminal radio button
                    if radio_value and list_type.lower() in radio_value.lower():
                        # Try JavaScript click
                        driver.execute_script("arguments[0].checked = true;", radio)
                        driver.execute_script("arguments[0].click();", radio)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", radio)
                        
                        # Verify it's checked
                        if radio.is_selected():
                            st.success(f"✅ Selected '{list_type}' list type")
                            radio_selected = True
                            break
                except:
                    continue
            
            # Method 2: Try finding by label text
            if not radio_selected:
                try:
                    labels = driver.find_elements(By.TAG_NAME, "label")
                    for label in labels:
                        label_text = label.text.strip().lower()
                        if list_type.lower() in label_text:
                            # Try to click the label
                            driver.execute_script("arguments[0].click();", label)
                            st.success(f"✅ Selected '{list_type}' list type (via label)")
                            radio_selected = True
                            break
                except:
                    pass
            
            if not radio_selected:
                st.warning(f"⚠️ Could not auto-select '{list_type}'. Please select manually.")
        except Exception as e:
            st.warning(f"List type selection issue: {e}")
        
        # Step 6: Wait for user to complete form and CAPTCHA
        st.info("🔐 Please complete the following in the browser:")
        st.markdown("""
        ### Manual Steps Required:
        1. **Check Court Complex** - Verify it's selected correctly
        2. **Select Court/Judge** - Choose from the dropdown (if not auto-selected)
        3. **Select Date** - Click calendar and pick the date (if not auto-set)
        4. **Select Civil/Criminal** - Verify the correct radio button is selected
        5. **Enter CAPTCHA** - Type the code shown in the image
        6. **Click Submit** - Click the submit button
        7. **Wait** - The script will automatically capture the results
        """)
        
        st.warning("⏳ You have 45 seconds to complete the form and submit...")
        
        # Countdown with progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        wait_time = 45
        for i in range(wait_time):
            progress_bar.progress((i + 1) / wait_time)
            status_text.text(f"⏰ Time remaining: {wait_time - i} seconds")
            time.sleep(1)
        
        progress_bar.empty()
        status_text.empty()
        
        # Get the page source
        raw_html = driver.page_source
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        # Parse cause list tables with sections
        all_sections_data = []
        
        # Find all tables
        tables = soup.find_all('table')
        
        if len(tables) > 0:
            st.info(f"Found {len(tables)} table(s) on the page")
            
            # Common headers for Delhi court cause lists
            standard_headers = ['Serial Number', 'Case Type/Case Number/Case Year', 'Party Name', 'Advocate']
            
            for table in tables:
                rows = table.find_all('tr')
                
                if len(rows) < 2:  # Skip tables with no data rows
                    continue
                
                # Check if this is a calendar table (skip it)
                first_row_text = rows[0].get_text(strip=True).lower()
                is_calendar = False
                
                # Look for calendar indicators
                if any(month in first_row_text for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                    is_calendar = True
                
                # Check if first data row contains mostly numbers (likely a calendar)
                if not is_calendar and len(rows) > 1:
                    first_data_row = rows[1]
                    cells = first_data_row.find_all('td')
                    if cells:
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        # If most cells are just numbers 1-31, it's likely a calendar
                        numeric_cells = sum(1 for text in cell_texts if text.isdigit() and 1 <= int(text) <= 31)
                        if numeric_cells > len(cells) * 0.7:  # More than 70% are date numbers
                            is_calendar = True
                
                if is_calendar:
                    st.info("⏭️ Skipping calendar table")
                    continue
                
                # Try to find the section name by looking at previous siblings or parent elements
                section_name = "Cases"
                
                # Look for heading before the table
                prev_element = table.find_previous(['h1', 'h2', 'h3', 'h4', 'strong', 'b', 'p'])
                if prev_element:
                    section_text = prev_element.get_text(strip=True)
                    if section_text and len(section_text) < 100:  # Reasonable section name length
                        section_name = section_text
                
                # Extract headers from the table
                header_row = rows[0]
                header_cells = header_row.find_all(['th', 'td'])
                table_headers = [cell.text.strip() for cell in header_cells] if header_cells else []
                
                # Check if this looks like a valid cause list table
                # Valid tables should have headers like "Serial Number", "Case", "Party", etc.
                is_valid_table = False
                if table_headers:
                    header_text = ' '.join(table_headers).lower()
                    if any(keyword in header_text for keyword in ['serial', 'case', 'party', 'advocate', 'petitioner', 'respondent']):
                        is_valid_table = True
                
                if not is_valid_table:
                    # Check if data rows look like case data (contains case numbers like T P (CRL)/19/2025)
                    if len(rows) > 1:
                        sample_text = ' '.join([cell.get_text() for cell in rows[1].find_all('td')])
                        if any(pattern in sample_text for pattern in ['/', '(', ')', 'Vs', 'vs', 'V/s', 'v/s']):
                            is_valid_table = True
                
                if not is_valid_table:
                    st.info(f"⏭️ Skipping non-cause-list table")
                    continue
                
                st.success(f"✅ Processing valid cause list table: {section_name}")
                
                # Extract data rows
                for row in rows[1:]:
                    cols = row.find_all('td')
                    if cols and len(cols) >= 3:  # Valid data row (at least 3 columns)
                        row_data = [col.text.strip() for col in cols]
                        
                        # Skip rows that are mostly empty or contain only numbers
                        non_empty_cells = [cell for cell in row_data if cell]
                        if len(non_empty_cells) < 2:
                            continue
                        
                        # Skip rows where all cells are just single/double digit numbers (calendar dates)
                        all_numbers = all(cell.isdigit() and len(cell) <= 2 for cell in row_data if cell)
                        if all_numbers:
                            continue
                        
                        # Add section name as the first column
                        row_with_section = [section_name] + row_data
                        all_sections_data.append(row_with_section)
            
            if all_sections_data:
                # Add "Section" as the first header
                final_headers = ['Section'] + standard_headers
                return all_sections_data, final_headers, raw_html
            else:
                return None, None, "No valid cause list data found in tables"
        else:
            return None, None, "No tables found on the page"

    except Exception as e:
        return None, None, f"An error occurred during cause list fetch: {e}"
    finally:
        time.sleep(5)  # Give time to see results
        driver.quit()

st.set_page_config(page_title="Court Data Fetcher", layout="wide")
st.title("⚖️ Indian Courts Case Data Fetcher & Automation Tool")
setup_database()
tab1, tab2, tab3 = st.tabs(["🔎 Fetch New Case Data", "📋 Fetch Cause List", "🗂️ View History"])

with tab1:
    st.header("1. Select Court")
    sel_col1, sel_col2, sel_col3 = st.columns(3)
    with sel_col1:
        state_name = st.text_input("State Name", "Delhi")
    with sel_col2:
        district_name = st.text_input("District Name", "South West")
    with sel_col3:
        court_complex_name = st.text_input("Court Complex", "Dwarka Courts")
    
    st.header("2. Enter Case Details")
    
    st.info("💡 Tip: The available case types will be shown after selecting the court. Common types are listed below.")
    
    with st.form("case_form"):
        case_col1, case_col2, case_col3 = st.columns(3)
        with case_col1:
            # Common case types based on Delhi courts
            case_type_options = [
                "CS (COMM) - CIVIL SUIT (COMMERCIAL)",
                "OMP (COMM) - COMMERCIAL ARBITRATION U/S 34",
                "CA - CRIMINAL APPEAL",
                "CC - CORRUPTION CASES",
                "CR Cases - CRIMINAL CASE",
                "Cr Rev - CRIMINAL REVISION",
                "CS - CIVIL SUIT FOR DJ ADJ",
                "CT Cases - COMPLAINT CASES",
                "EX - EXECUTION",
                "HMA - HINDU MARRIAGE ACT",
                "MACT - M.A.C.T.",
                "MISC CRL - MISC. CASES",
                "MISC DJ - MISC. CASES FOR DJ ADJ",
                "SC - SESSIONS CASE",
                "Other (type exact text from website)"
            ]
            case_type_select = st.selectbox("Case Type", case_type_options)
            if case_type_select == "Other (type exact text from website)":
                case_type = st.text_input("Enter Case Type (exact text)", placeholder="e.g., CS (COMM) - CIVIL SUIT (COMMERCIAL)")
            else:
                case_type = case_type_select
        with case_col2:
            case_number = st.text_input("Case Number", placeholder="e.g., 1234")
        with case_col3:
            current_year = pd.Timestamp.now().year
            case_year = st.selectbox("Year", list(range(current_year, 1989, -1)))
        
        submitted = st.form_submit_button("🚀 Fetch Case Details")

    if submitted:
        if not all([case_type, case_number, case_year, state_name, district_name, court_complex_name]):
            st.error("Please fill in all the fields before submitting.")
        else:
            with st.spinner(f"Processing... A browser window will open."):
                parsed_data, response_text = fetch_case_data(case_type, case_number, case_year, state_name, district_name, court_complex_name)
                if parsed_data:
                    st.success("Data Fetched Successfully!")
                    store_query_result(case_type, case_number, case_year, parsed_data, response_text)
                    st.subheader("Fetched Case Details")
                    st.json(parsed_data)
                    
                    # Download options
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # CSV Download
                        df_case = pd.DataFrame([parsed_data])
                        csv = df_case.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv,
                            file_name=f"case_{case_type}_{case_number}_{case_year}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        # PDF Download
                        pdf_buffer = generate_case_details_pdf(parsed_data, case_type, case_number, case_year)
                        st.download_button(
                            label="📄 Download as PDF",
                            data=pdf_buffer,
                            file_name=f"case_{case_type}_{case_number}_{case_year}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.error(f"Failed to fetch data. Reason: {response_text}")

with tab2:
    st.header("📋 Fetch Daily Cause List")
    st.info("💡 Fetch the daily cause list from court website.")
    
    with st.form("cause_list_form"):
        form_col1, form_col2 = st.columns(2)
        
        with form_col1:
            cl_court_complex = st.selectbox(
                "Court Complex",
                [
                    "Patiala House Court Complex",
                    "Tis Hazari Courts Complex",
                    "Karkardooma Courts Complex",
                    "Rohini Courts Complex",
                    "Dwarka Courts Complex",
                    "Saket Courts Complex",
                    "Rouse Avenue Courts Complex"
                ],
                help="Select the Delhi court complex"
            )
        
        with form_col2:
            cl_list_type = st.radio(
                "List Type",
                ["Civil", "Criminal"],
                horizontal=True,
                help="Select Civil or Criminal cause list"
            )
        
        cl_court_number = st.text_input(
            "Court Number / Judge Name (Optional)",
            placeholder="e.g., 1 Ms. Anju Bajaj Chandna - Principal District and Sessions Judge",
            help="Enter the court number and judge name. Leave blank to see all available options."
        )
        
        cl_date = st.date_input(
            "Cause List Date",
            help="Select the date for which you want to fetch the cause list"
        )
        # Format date as MM/DD/YYYY for Delhi courts website
        formatted_date = cl_date.strftime("%m/%d/%Y")
        
        cl_submitted = st.form_submit_button("🚀 Fetch Cause List")
    
    if cl_submitted:
        with st.spinner(f"Processing... A browser window will open."):
            cause_list_data, headers, response = fetch_cause_list_delhi(
                cl_court_complex,
                cl_court_number,
                formatted_date,
                cl_list_type
            )
            
            if cause_list_data:
                st.success(f"✅ Cause List Fetched Successfully for {formatted_date}!")
                
                # Store in database
                store_cause_list_result(
                    cl_court_complex,
                    cl_court_number if cl_court_number else "All Courts",
                    formatted_date,
                    cl_list_type,
                    len(cause_list_data)
                )
                
                # Display header information
                st.markdown(f"""
                ### 📋 {cl_list_type} Cause List
                **Court Complex:** {cl_court_complex}  
                **Date:** {formatted_date}  
                **Total Cases:** {len(cause_list_data)}
                """)
                
                # Display as dataframe
                if cause_list_data:
                    # Check if headers match data columns
                    if headers and len(cause_list_data) > 0:
                        # Find the maximum number of columns in the data
                        max_cols = max(len(row) for row in cause_list_data)
                        
                        # If headers don't match, create generic headers or pad existing ones
                        if len(headers) != max_cols:
                            st.warning(f"Headers count ({len(headers)}) doesn't match data columns ({max_cols}). Using generic column names.")
                            # Use existing headers and add generic ones for missing columns
                            if len(headers) < max_cols:
                                headers = headers + [f"Column_{i+1}" for i in range(len(headers), max_cols)]
                            else:
                                headers = headers[:max_cols]
                        
                        # Ensure all rows have the same number of columns
                        normalized_data = []
                        for row in cause_list_data:
                            if len(row) < max_cols:
                                # Pad short rows with empty strings
                                row = row + [''] * (max_cols - len(row))
                            elif len(row) > max_cols:
                                # Truncate long rows
                                row = row[:max_cols]
                            normalized_data.append(row)
                        
                        df = pd.DataFrame(normalized_data, columns=headers)
                    else:
                        # No headers, just use the data as-is
                        df = pd.DataFrame(cause_list_data)
                    
                    # Display full table
                    st.dataframe(df, use_container_width=True)
                    
                    # Show section-wise breakdown if 'Section' column exists
                    if 'Section' in df.columns:
                        st.markdown("---")
                        st.subheader("📊 Section-wise Breakdown")
                        section_counts = df['Section'].value_counts()
                        
                        col1, col2 = st.columns([2, 3])
                        with col1:
                            st.dataframe(section_counts.reset_index().rename(columns={'index': 'Section', 'Section': 'Count'}), use_container_width=True)
                        
                        with col2:
                            # Show expandable sections
                            for section in df['Section'].unique():
                                section_df = df[df['Section'] == section]
                                with st.expander(f"📂 {section} ({len(section_df)} cases)"):
                                    st.dataframe(section_df.drop('Section', axis=1), use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Download options
                    st.subheader("📥 Download Options")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # CSV Download
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv,
                            file_name=f"cause_list_{cl_court_complex.replace(' ', '_')}_{formatted_date}_{cl_list_type}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        # PDF Download
                        pdf_buffer = generate_cause_list_pdf(df, cl_court_complex, formatted_date, cl_list_type)
                        st.download_button(
                            label="📄 Download as PDF",
                            data=pdf_buffer,
                            file_name=f"cause_list_{cl_court_complex.replace(' ', '_')}_{formatted_date}_{cl_list_type}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.warning("No cases found in the cause list.")
            else:
                st.error(f"Failed to fetch cause list. Reason: {response}")

with tab3:
    st.header("📊 Query History")
    
    if st.button("🔄 Refresh History"):
        st.rerun()
    
    case_df, cause_list_df = view_all_data()
    
    # Create sub-tabs for different history types
    history_tab1, history_tab2 = st.tabs(["📋 Case Status History", "📅 Cause List History"])
    
    with history_tab1:
        st.subheader("Case Status Queries")
        if not case_df.empty:
            st.info(f"Total queries: {len(case_df)}")
            st.dataframe(case_df.drop('query_type', axis=1), use_container_width=True)
        else:
            st.info("No case status queries found.")
    
    with history_tab2:
        st.subheader("Cause List Queries")
        if not cause_list_df.empty:
            st.info(f"Total queries: {len(cause_list_df)}")
            # Rename columns for better display
            display_df = cause_list_df.drop('query_type', axis=1).copy()
            display_df = display_df.rename(columns={
                'id': 'ID',
                'timestamp': 'Timestamp',
                'court_complex': 'Court Complex',
                'list_date': 'Date',
                'list_type': 'Type',
                'total_cases': 'Total Cases'
            })
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No cause list queries found.")