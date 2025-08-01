[日本語](README-jp.md)
[العربية](README-ar.md)
[Português](README-pt.md)
[Español](README-es.md)
# Web Scraping and Data Processing Application

## Overview
This Flask-based web application provides a comprehensive solution for scraping product information from e-commerce websites and processing the collected data. The application supports two distinct scraping modes for different types of product pages (bags and jewelry) and includes functionality to upload the scraped data to a remote server.

## Key Features

### 1. Dual Scraping Modes
- **Bag Product Scraper**: Specialized for bag product pages with specific CSS selectors
- **Jewelry Product Scraper**: Optimized for jewelry product pages with different page structures

### 2. Comprehensive Data Extraction
- Extracts multiple product attributes including:
  - Title and description
  - Pricing information
  - Product images (up to 8 per product)
  - Product options/variants
  - Customer reviews
  - SEO keywords
  - Technical specifications

### 3. Robust Error Handling
- Multiple fallback mechanisms when primary selectors fail
- Comprehensive exception handling for various web scraping scenarios
- Timeout management for slow-loading pages

### 4. Data Processing and Export
- Automatic CSV export of scraped data
- JSON data cleaning and validation
- HTML description generation with embedded images

### 5. Web Interface
- User-friendly form for submitting product page URLs
- Results display page showing scraped data
- API endpoint for data upload functionality

## Technical Implementation

### Core Technologies
- **Flask**: Web application framework
- **Selenium**: Web scraping and browser automation
- **Pandas**: Data processing and CSV export
- **WebDriver Manager**: Automated browser driver management

### Advanced Features
- Dynamic waiting for page elements
- Multiple fallback selectors for robust scraping
- Relative-to-absolute URL conversion
- Asynchronous processing of multiple product pages
- Data validation and cleaning

## Usage Scenarios
1. **E-commerce Competitor Analysis**: Scrape product data from competitor websites
2. **Product Catalog Migration**: Transfer product information between platforms
3. **Price Monitoring**: Track price changes over time
4. **Content Aggregation**: Collect product information for comparison websites

## Installation & Requirements
- Python 3.x
- Chrome browser
- Required Python packages:
  ```
  flask
  selenium
  pandas
  webdriver-manager
  requests
  ```

Note: The application includes extensive logging throughout the scraping process to help diagnose issues and monitor progress.
