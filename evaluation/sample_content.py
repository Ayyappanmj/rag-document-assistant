"""Fictional documents used ONLY as an evaluation fixture. Every company, number and policy is invented.
make_sample_pdfs.py turns this into PDFs; questions.json asks about these facts."""

SAMPLE_DOCS: dict[str, list[tuple[str, str]]] = {
    "Annual_Report.pdf": [
        ("Company Overview",
         "Northwind Analytics is a software company that builds data analytics products for enterprises. "
         "The company was founded in 2012 and is headquartered in Pune, India. As of 31 March 2025, "
         "Northwind Analytics employed 1,842 people across six offices. The company serves 640 enterprise "
         "customers in banking, healthcare and retail. This report covers the financial year ended "
         "31 March 2025, referred to as FY2025."),
        ("Financial Highlights",
         "Revenue for FY2025 was USD 84.6 million, compared with USD 71.7 million in FY2024, an increase "
         "of 18 percent. Net profit for FY2025 was USD 12.3 million, compared with USD 9.8 million in "
         "FY2024. Operating margin was 21.4 percent. The board approved a dividend of USD 0.25 per share "
         "for FY2025."),
        ("Revenue Sources",
         "Cloud subscriptions were the largest source of revenue and contributed 58 percent of total "
         "revenue in FY2025. Professional services contributed 27 percent of revenue. Licence fees "
         "contributed the remaining 15 percent."),
        ("Regional Performance",
         "North America was the largest region and generated 46 percent of revenue in FY2025. Europe "
         "generated 31 percent and Asia-Pacific generated 23 percent. Three large customers together "
         "accounted for 22 percent of total revenue."),
        ("Risks and Outlook",
         "The company identifies three main risks: currency fluctuations, dependence on a small number of "
         "large customers, and cybersecurity incidents. For FY2026 the company expects revenue growth of "
         "12 to 15 percent. The company plans to hire 300 engineers during FY2026."),
    ],
    "Financial_Statement.pdf": [
        ("Condensed Income Statement",
         "All amounts are in USD millions for the year ended 31 March 2025. Total revenue was 84.6. "
         "Cost of revenue was 31.2. Gross profit was 53.4. Net profit was 12.3."),
        ("Condensed Balance Sheet",
         "All amounts are in USD millions as at 31 March 2025. Total assets were 120.5. Cash and cash "
         "equivalents were 41.2. Total liabilities were 48.7. Shareholders equity was 71.8."),
    ],
    "Company_Policy.pdf": [
        ("Leave Policy",
         "Full-time employees receive 24 days of paid annual leave per calendar year. Up to 5 unused days "
         "of annual leave may be carried forward to the next year. Employees also receive 10 days of paid "
         "sick leave per year."),
        ("Remote Work and Expenses",
         "Employees may work remotely up to 3 days per week with manager approval. Core working hours are "
         "10:00 to 16:00 India Standard Time. Expenses above USD 200 require prior manager approval. "
         "Expense claims must be submitted within 30 days of the purchase."),
        ("Information Security",
         "Passwords must be at least 14 characters long. Multi-factor authentication is required for all "
         "company systems. Security incidents must be reported within 24 hours of discovery. All employees "
         "must complete security training once a year."),
    ],
}
