import dash
from dash import dcc, html, Input, Output, State, dash_table, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta
import json
import io



# --- Data Loading Function ---
def load_data():
    """
    Loads and processes all necessary CSV data for the dashboard.
    Assumes CSVs are in a 'data/' subdirectory relative to app.py.
    Returns a dictionary where each DataFrame is converted to a JSON string.
    """
    data = {}
    base_dir = os.path.dirname(__file__) # Gets the directory 
    data_dir = os.path.join(base_dir, 'data')

    try:
        products_path = os.path.join(data_dir, 'products_and_suppliers_combined.csv')
        df_products = pd.read_csv(products_path)
        df_products = df_products.rename(columns={'SupplierName': 'Supplier'}) 
        df_products['ExpiryDate'] = pd.to_datetime(df_products['ExpiryDate'], errors='coerce')

        if 'Weight' not in df_products.columns:
            df_products['Weight'] = 0.5 # Default weight of 0.5 kg per product entry for waste calculation

        data['products'] = df_products.to_json(date_format='iso', orient='split')

        sales_path = os.path.join(data_dir, 'sales_data.csv')
        df_sales = pd.read_csv(sales_path)
        df_sales['SaleDate'] = pd.to_datetime(df_sales['SaleDate'])
        data['sales'] = df_sales.to_json(date_format='iso', orient='split')

        inventory_path = os.path.join(data_dir, 'inventory_movements.csv')
        df_inventory = pd.read_csv(inventory_path)
        df_inventory['MovementDate'] = pd.to_datetime(df_inventory['MovementDate'])
        data['inventory'] = df_inventory.to_json(date_format='iso', orient='split')

        locations_path = os.path.join(data_dir, 'locations.csv')
        df_locations = pd.read_csv(locations_path)
        data['locations'] = df_locations.to_json(date_format='iso', orient='split')

        holidays_path = os.path.join(data_dir, 'holidays.csv')
        df_holidays = pd.read_csv(holidays_path)
        df_holidays['HolidayDate'] = pd.to_datetime(df_holidays['HolidayDate'])
        data['holidays'] = df_holidays.to_json(date_format='iso', orient='split')

        promotions_path = os.path.join(data_dir, 'promotions.csv')
        df_promotions = pd.read_csv(promotions_path)
        df_promotions['PromotionStartDate'] = pd.to_datetime(df_promotions['PromotionStartDate'])
        df_promotions['PromotionEndDate'] = pd.to_datetime(df_promotions['PromotionEndDate'])
        data['promotions'] = df_promotions.to_json(date_format='iso', orient='split')

        weather_path = os.path.join(data_dir, 'weather_data.csv')
        df_weather = pd.read_csv(weather_path)
        df_weather['WeatherDate'] = pd.to_datetime(df_weather['WeatherDate'])
        data['weather'] = df_weather.to_json(date_format='iso', orient='split')

        print("All data loaded successfully.")
    except FileNotFoundError as e:
        print(f"Error loading data: {e}. Make sure the 'data' directory and CSV files exist.")
        data = {
            'products': pd.DataFrame().to_json(date_format='iso', orient='split'),
            'sales': pd.DataFrame().to_json(date_format='iso', orient='split'),
            'inventory': pd.DataFrame().to_json(date_format='iso', orient='split'),
            'locations': pd.DataFrame().to_json(date_format='iso', orient='split'),
            'holidays': pd.DataFrame().to_json(date_format='iso', orient='split'),
            'promotions': pd.DataFrame().to_json(date_format='iso', orient='split'),
            'weather': pd.DataFrame().to_json(date_format='iso', orient='split')
        }
    return data

# Initialize app with Bootstrap themes
app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.BOOTSTRAP,
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css',
    '/assets/custom.css'
],
                suppress_callback_exceptions=True 
)

# Initial data load
app_data = load_data()

# --- Helper Functions for Data Calculations ---
def get_realtime_metrics(stored_data_json):
    df_products = pd.read_json(io.StringIO(stored_data_json['products']), orient='split') if stored_data_json.get('products') else pd.DataFrame()
    df_inventory = pd.read_json(io.StringIO(stored_data_json['inventory']), orient='split') if stored_data_json.get('inventory') else pd.DataFrame()

    if not df_products.empty and 'ExpiryDate' in df_products.columns:
        df_products['ExpiryDate'] = pd.to_datetime(df_products['ExpiryDate'], errors='coerce')

    if not df_inventory.empty and 'MovementDate' in df_inventory.columns:
        df_inventory['MovementDate'] = pd.to_datetime(df_inventory['MovementDate'])

    if not df_inventory.empty:
        stock_in = df_inventory[df_inventory['MovementType'] == 'IN']['Quantity'].sum()
        stock_out = df_inventory[df_inventory['MovementType'] == 'OUT']['Quantity'].sum()
        items_in_stock = stock_in - stock_out
    else:
        items_in_stock = 0

    prev_items_in_stock = 12900 # Example dummy value
    stock_change_percent = ((items_in_stock - prev_items_in_stock) / prev_items_in_stock) * 100 if prev_items_in_stock else 0

    reorder_recommendations = 15 # Example dummy value
    prev_reorder_recommendations = 7 # Example dummy value
    reorder_change_percent = ((reorder_recommendations - prev_reorder_recommendations) / prev_reorder_recommendations) * 100 if prev_reorder_recommendations else 0

    if not df_products.empty:
        today = pd.to_datetime(datetime.now().date())
        expiring_items_count = df_products[
            (df_products['ExpiryDate'].notna()) &
            (df_products['ExpiryDate'] >= today) &
            (df_products['ExpiryDate'] <= today + timedelta(days=30))
        ].shape[0]
    else:
        expiring_items_count = 0

    prev_expiring_items = 8.4 # Example dummy value
    expiring_change_percent = ((expiring_items_count - prev_expiring_items) / prev_expiring_items) * 100 if prev_expiring_items else 0

    return {
        'items_in_stock': f"{items_in_stock:,.0f}",
        'stock_change': f"{stock_change_percent:+.0f}%", # Added + for positive change
        'stock_change_class': 'positive' if stock_change_percent >= 0 else 'negative',
        'reorder_recommendations': f"{reorder_recommendations}",
        'reorder_change': f"{reorder_change_percent:+.0f}%",
        'reorder_change_class': 'positive' if reorder_change_percent >= 0 else 'negative',
        'expiring_items': f"{expiring_items_count}",
        'expiring_change': f"{expiring_change_percent:+.0f}%",
        'expiring_change_class': 'negative' if expiring_change_percent >= 0 else 'positive', # Negative for expiring is 'bad'
    }

def get_sales_data_for_chart(stored_data_json):
    df_sales = pd.read_json(io.StringIO(stored_data_json['sales']), orient='split') if stored_data_json.get('sales') else pd.DataFrame()
    if df_sales.empty:
        return pd.DataFrame()
    df_sales['SaleDate'] = pd.to_datetime(df_sales['SaleDate'])
    monthly_sales = df_sales.set_index('SaleDate').resample('MS')['TotalPrice'].sum().reset_index()
    monthly_sales['Date_Label'] = monthly_sales['SaleDate'].dt.strftime('%b %Y')
    if len(monthly_sales) > 5:
        monthly_sales = monthly_sales.tail(5)
    return monthly_sales

def calculate_last_5_months_sales_change(stored_data_json):
    df_sales = pd.read_json(io.StringIO(stored_data_json['sales']), orient='split') if stored_data_json.get('sales') else pd.DataFrame()
    if df_sales.empty:
        return "0", "0%"
    df_sales['SaleDate'] = pd.to_datetime(df_sales['SaleDate'])
    today = pd.to_datetime(datetime.now().date())
    five_months_ago_start = today - pd.DateOffset(months=5)
    recent_sales_sum = df_sales[df_sales['SaleDate'] >= five_months_ago_start]['TotalPrice'].sum()
    ten_months_ago_start = today - pd.DateOffset(months=10)
    previous_period_sales_sum = df_sales[(df_sales['SaleDate'] >= ten_months_ago_start) & (df_sales['SaleDate'] < five_months_ago_start)]['TotalPrice'].sum()
    
    percentage_change = 0
    if previous_period_sales_sum > 0:
        percentage_change = ((recent_sales_sum - previous_period_sales_sum) / previous_period_sales_sum) * 100
    elif recent_sales_sum > 0: # Handle case where previous period sales were 0
        percentage_change = 100 
    return f"{recent_sales_sum:,.0f}", f"{percentage_change:+.0f}%"

def get_top_categories_in_profit(stored_data_json, top_n=5):
    df_sales = pd.read_json(io.StringIO(stored_data_json['sales']), orient='split') if stored_data_json.get('sales') else pd.DataFrame()
    df_products = pd.read_json(io.StringIO(stored_data_json['products']), orient='split') if stored_data_json.get('products') else pd.DataFrame()
    
    if df_sales.empty or df_products.empty:
        return pd.DataFrame(), 0

    df_sales['SaleDate'] = pd.to_datetime(df_sales['SaleDate'])
    
    # Merge sales data with relevant product data (Category and Cost)
    product_cols_to_merge = ['ProductID', 'Category', 'Cost']
    existing_product_cols = [col for col in product_cols_to_merge if col in df_products.columns]
    
    if len(existing_product_cols) < len(product_cols_to_merge):
        return pd.DataFrame(), 0 

    df_merged = pd.merge(df_sales, df_products[existing_product_cols], 
                         on='ProductID', how='left')
    
    # Robustness: Convert to numeric, fill NaN
    df_merged['Cost'] = pd.to_numeric(df_merged['Cost'], errors='coerce').fillna(0)
    df_merged['Quantity'] = pd.to_numeric(df_merged['Quantity'], errors='coerce').fillna(0)
    df_merged['TotalPrice'] = pd.to_numeric(df_merged['TotalPrice'], errors='coerce').fillna(0)
    
    df_merged['Category'] = df_merged['Category'].fillna('Unknown') 

    df_merged['Profit'] = df_merged['TotalPrice'] - (df_merged['Quantity'] * df_merged['Cost'])

    df_merged = df_merged.dropna(subset=['Profit'])
    
    if df_merged.empty:
        return pd.DataFrame(), 0

   
    today = datetime.now() 
    current_quarter_start = today - timedelta(days=90)
    
    df_quarterly_profit_data = df_merged[
        (df_merged['SaleDate'] >= current_quarter_start)
    ].copy() 
    
    # If no data in the current quarter after filtering, return empty
    if df_quarterly_profit_data.empty:
        return pd.DataFrame(), 0

    # --- NOW CALCULATE TOTAL PROFIT AND TOP CATEGORIES FROM THE FILTERED QUARTERLY DATA ---
    total_profit_current_quarter = df_quarterly_profit_data['Profit'].sum() 

    # Group by 'Category' and get top N categories by total profit for the CURRENT QUARTER
    category_profit = df_quarterly_profit_data.groupby('Category')['Profit'].sum().nlargest(top_n).reset_index()
    category_profit.columns = ['Category', 'Profit']
    
    # Filter out categories with non-positive profit if 'top categories' implies only profitable ones
    category_profit = category_profit[category_profit['Profit'] > 0]
    
    return category_profit, total_profit_current_quarter

def get_notifications(stored_data_json):
    df_products = pd.read_json(io.StringIO(stored_data_json['products']), orient='split') if stored_data_json.get('products') else pd.DataFrame()
    notifications = []

    if not df_products.empty and 'ExpiryDate' in df_products.columns:
        df_products['ExpiryDate'] = pd.to_datetime(df_products['ExpiryDate'], errors='coerce')

    today = pd.to_datetime(datetime.now().date())
    
    # Dynamic: Expiring products (top 2)
    expiring_soon_products = df_products[
        (df_products['ExpiryDate'].notna()) &
        (df_products['ExpiryDate'] >= today) &
        (df_products['ExpiryDate'] <= today + timedelta(days=7))
    ].head(2) # Limit to a few to avoid overwhelming notifications
    for _, row in expiring_soon_products.iterrows():
        days_left = (row['ExpiryDate'] - today).days
        notifications.append({
            'type': 'expiring',
            'text': f"Item {row['ProductName']} expiring in {days_left} days!",
            'time': f"{days_left} days left"
        })


    # Static notifications (ensure they are not duplicated if the function is called multiple times)
    notifications.append({'type': 'new_supplier', 'text': "New supplier 'Tech Solutions Inc.' onboarding required.", 'time': "6 hours ago"})
    notifications.append({'type': 'waste', 'text': "Waste report for Q1 needs review.", 'time': "1 day ago"})
    notifications.append({'type': 'low_stock', 'text': "Item XYZ is low in stock: 10 units left!", 'time': "3m ago"})
    notifications.append({'type': 'pending_invoice', 'text': "New supplier ABC has pending invoice.", 'time': "1h ago"})

    return notifications

def get_monthly_waste_data_for_chart(stored_data_json, num_months=3): 
    """
    Calculates monthly waste data for the bar chart, showing the last 'num_months' months.
    Labels months as Jan, Feb, etc.
    """
    df_products = pd.read_json(io.StringIO(stored_data_json['products']), orient='split') if stored_data_json.get('products') else pd.DataFrame()

    if df_products.empty:
        return {'months': [], 'waste_kilos': [], 'df': pd.DataFrame({'Month': [], 'Waste_KGS': []})}

    df_products['ExpiryDate'] = pd.to_datetime(df_products['ExpiryDate'], errors='coerce')
    today = pd.to_datetime(datetime.now().date())
    
    # Filter for items that have expired before 'today'
    expired_items = df_products[
        (df_products['ExpiryDate'].notna()) &
        (df_products['ExpiryDate'] < today)
    ].copy()

    if expired_items.empty:
        return {'months': [], 'waste_kilos': [], 'df': pd.DataFrame({'Month': [], 'Waste_KGS': []})}

    
    expired_items['ExpiryMonth'] = expired_items['ExpiryDate'].dt.to_period('M')
    monthly_waste = expired_items.groupby('ExpiryMonth')['Weight'].sum().reset_index()
    monthly_waste.columns = ['MonthPeriod', 'Waste_KGS']

    
    end_month = today.to_period('M')
    all_periods = pd.period_range(end=end_month, periods=2 * num_months, freq='M')

    full_monthly_data = pd.DataFrame({'MonthPeriod': all_periods})
    full_monthly_data = pd.merge(full_monthly_data, monthly_waste, on='MonthPeriod', how='left').fillna(0)
    
    
    display_df = full_monthly_data.tail(num_months).copy()
    
    
    display_df['Month'] = display_df['MonthPeriod'].dt.strftime('%b')

    return {
        'months': display_df['Month'].tolist(),
        'waste_kilos': display_df['Waste_KGS'].tolist(),
        'df': display_df[['Month', 'Waste_KGS']]
    }

def calculate_overall_quarterly_waste(stored_data_json): # Renamed function
    """
    Calculates the total waste for the last 3 months (quarter) and its change from the previous 3 months.
    This is used for the summary text.
    """
    df_products = pd.read_json(io.StringIO(stored_data_json['products']), orient='split') if stored_data_json.get('products') else pd.DataFrame()

    if df_products.empty:
        return {'total_waste_text': "0 kgs", 'change_text': "0%"}

    df_products['ExpiryDate'] = pd.to_datetime(df_products['ExpiryDate'], errors='coerce')
    today = pd.to_datetime(datetime.now().date())
    
    expired_items = df_products[
        (df_products['ExpiryDate'].notna()) &
        (df_products['ExpiryDate'] < today)
    ].copy()

    if expired_items.empty:
        return {'total_waste_text': "0 kgs", 'change_text': "0%"}

    # Calculate waste for the last 3 months (current quarter)
    end_date_current = today
    start_date_current = end_date_current - pd.DateOffset(months=3) # 3 months for a quarter
    
    current_period_waste = expired_items[
        (expired_items['ExpiryDate'] >= start_date_current) &
        (expired_items['ExpiryDate'] < end_date_current)
    ]['Weight'].sum()

    # Calculate waste for the previous 3 months (previous quarter)
    end_date_previous = start_date_current
    start_date_previous = end_date_previous - pd.DateOffset(months=3) # Previous 3 months

    previous_period_waste = expired_items[
        (expired_items['ExpiryDate'] >= start_date_previous) &
        (expired_items['ExpiryDate'] < end_date_previous)
    ]['Weight'].sum()

    waste_change_percent = 0
    if previous_period_waste > 0:
        waste_change_percent = ((current_period_waste - previous_period_waste) / previous_period_waste) * 100
    else:
        waste_change_percent = 100 if current_period_waste > 0 else 0

    total_waste_text = f"{current_period_waste:,.0f} kgs"
    change_text = f"{waste_change_percent:+.0f}%"

    return {'total_waste_text': total_waste_text, 'change_text': change_text}


def get_expiry_data(stored_data_json, view_filter='All'):
    print(f"get_expiry_data received view_filter: {view_filter}")
    df_products = pd.read_json(io.StringIO(stored_data_json['products']), orient='split') if stored_data_json.get('products') else pd.DataFrame()
    
    if df_products.empty:
        return pd.DataFrame(), {'expired': '0', 'expiring_7': '0 (0 units)', 'expiring_30': '0 (0 units)'}
    

    df_products['ExpiryDate'] = pd.to_datetime(df_products['ExpiryDate'], errors='coerce')
    today = pd.to_datetime(datetime.now().date())

    # Calculate expiry statuses
    df_products['Status'] = 'Good'
    df_products.loc[df_products['ExpiryDate'] < today, 'Status'] = 'Expired'
    df_products.loc[(df_products['Status'] != 'Expired') & 
                    (df_products['ExpiryDate'] >= today) & 
                    (df_products['ExpiryDate'] <= today + timedelta(days=7)), 
                    'Status'] = 'Expiring Soon'
    
     # Logic for 'X Days Remaining'
    nearing_expiry_mask = (df_products['Status'] != 'Expired') & \
                          (df_products['Status'] != 'Expiring Soon') & \
                          (df_products['ExpiryDate'] > today + timedelta(days=7)) & \
                          (df_products['ExpiryDate'] <= today + timedelta(days=30))
    
    # Calculate days remaining for products that fit this mask
    # Ensure to convert ExpiryDate and today to date for accurate day difference, then to timedelta
    days_remaining_series = (df_products.loc[nearing_expiry_mask, 'ExpiryDate'].dt.date - today.date()).apply(lambda x: x.days)

    # Update the 'Status' column with the exact days remaining 
    df_products.loc[nearing_expiry_mask, 'Status'] = 'Nearing Expiry (' + days_remaining_series.astype(str) + ' Days)'
    # --- END Status Calculation ---

  # --- Filtering Logic ---
    display_df = df_products.copy()

    if view_filter == 'Expired': 
        display_df = display_df[display_df['Status'] == 'Expired']
    elif view_filter == 'Expiring Soon': # Includes both 'Expiring Soon' AND 'Nearing Expiry (X Days)'
        display_df = display_df[
            (display_df['Status'] == 'Expiring Soon') | 
            (display_df['Status'].str.contains('Nearing Expiry \\(', na=False)) # ESCAPED PARENTHESIS
        ]
    elif view_filter == 'Expiring in 30 Days': # ONLY includes 'Nearing Expiry (X Days)'
        display_df = display_df[display_df['Status'].str.contains('Nearing Expiry \\(', na=False)] # ESCAPED PARENTHESIS
    elif view_filter == 'All Items': 
        display_df = df_products.copy() 
    # --- END Filtering Logic ---


    # Format ExpiryDate for display
    display_df['ExpiryDate'] = display_df['ExpiryDate'].dt.strftime('%d %b %Y')

    # Prepare data for the table
    table_data = display_df[['ProductName', 'ProductID', 'quantity', 'ExpiryDate', 'Status']].rename(columns={
        'ProductName': 'PRODUCT NAME',
        'ProductID': 'STOCK ID',
        'quantity': 'QUANTITY',
        'ExpiryDate': 'EXPIRY DATE',
        'Status': 'STATUS'
    })

    # Calculate expiry overview metrics
    expired_count = df_products[df_products['Status'] == 'Expired'].shape[0]
    expired_units = df_products[df_products['Status'] == 'Expired']['quantity'].sum()

    expiring_7_count = df_products[df_products['Status'] == 'Expiring Soon'].shape[0]
    expiring_7_units = df_products[df_products['Status'] == 'Expiring Soon']['quantity'].sum()

    expiring_30_count = df_products[
        (df_products['Status'] == 'Expiring Soon') | 
        (df_products['Status'].str.contains('Nearing Expiry \\(', na=False)) 
    ].shape[0]
    expiring_30_units = df_products[
        (df_products['Status'] == 'Expiring Soon') | 
        (df_products['Status'].str.contains('Nearing Expiry \\(', na=False)) 
    ]['quantity'].sum()

    expiry_overview = {
        'expired': f"{expired_count} item{'s' if expired_count != 1 else ''} ({expired_units} units)",
        'expiring_7': f"{expiring_7_count} item{'s' if expiring_7_count != 1 else ''} ({expiring_7_units} units)",
        'expiring_30': f"{expiring_30_count} item{'s' if expiring_30_count != 1 else ''} ({expiring_30_units} units)"
    }

    return table_data, expiry_overview


# --- Layout Components ---

sidebar = html.Div(
    [
        html.Div(
            [
                html.Img(src="/assets/invaai_logo.png", className="sidebar-logo"),
                html.H2("InvAI", className="sidebar-title"),
                html.P("The Brain Behind Your Inventory", className="sidebar-subtitle"),
            ],
            className="sidebar-header"
        ),
        dbc.Nav(
            [
                dbc.NavLink([html.I(className="bi bi-speedometer2 me-2"), "Dashboard"], href="/", active="exact", className="nav-link-item"),
                dbc.NavLink([html.I(className="bi bi-box-seam me-2"), "Stock Management"], href="/stock-management", active="exact", className="nav-link-item"),
                dbc.NavLink([html.I(className="bi bi-arrow-repeat me-2"), "Reorder Recommendations"], href="/reorder-recommendations", active="exact", className="nav-link-item"),
                dbc.NavLink([html.I(className="bi bi-calendar-x me-2"), "Expiry Management"], href="/expiry-management", active="exact", className="nav-link-item"),
                dbc.NavLink([html.I(className="bi bi-clipboard-data me-2"), "Scenario Planner"], href="/scenario-planner", active="exact", className="nav-link-item"),
                dbc.NavLink([html.I(className="bi bi-graph-up me-2"), "Sales & Trends Report"], href="/sales-trends", active="exact", className="nav-link-item"),
                dbc.NavLink([html.I(className="bi bi-recycle me-2"), "Sustainability Tracker"], href="/sustainability", active="exact", className="nav-link-item"),
                dbc.NavLink([html.I(className="bi bi-truck me-2"), "Supplier"], href="/supplier", active="exact", className="nav-link-item"),
                dbc.NavLink([html.I(className="bi bi-gear me-2"), "Settings"], href="/settings", active="exact", className="nav-link-item"),
            ],
            vertical=True,
            pills=True,
            className="sidebar-nav"
        ),
        html.Div(
            [
                html.A([html.I(className="bi bi-box-arrow-right me-2"), "Logout"], href="/logout", className="logout-link"),
            ],
            className="sidebar-footer"
        )
    ],
    className="sidebar"
)

# Dashboard Content
dashboard_content = html.Div(
    [
        html.Div(
            [
                html.H3("Dashboard Overview", className="dashboard-header-title"),
                html.Img(src="/assets/user_avatar.png", className="user-avatar")
            ],
            className="dashboard-header"
        ),
        dbc.Card(
            [
                html.Div(
                    [
                        html.H4("Welcome back, Sarah!", className="welcome-banner-title"),
                        html.P("Efficiently manage your stock with smart, sustainable insights", className="welcome-banner-subtitle"),
                        dbc.Button("Explore Dashboard", className="welcome-banner-button"),
                    ],
                    className="welcome-banner-text"
                )
            ],
            className="welcome-banner",
            style={'background-image': 'url("/assets/welcome_banner_bg.png")'}
        ),
        html.H4("Real-Time Metrics", className="section-title"),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            html.P("Items In Stock", className="metric-label"),
                            html.Div([
                                html.H3(id="items-in-stock-value", className="metric-value"),
                                html.Span(id="items-in-stock-change", className="metric-change")
                            ], className="d-flex align-items-center"),
                        ],
                        className="metric-card"
                    ),
                    md=4
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            html.P("Reorder Recommendations", className="metric-label"),
                            html.Div([
                                html.H3(id="reorder-recommendations-value", className="metric-value"),
                                html.Span(id="reorder-recommendations-change", className="metric-change")
                            ], className="d-flex align-items-center"),
                        ],
                        className="metric-card"
                    ),
                    md=4
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            html.P("Expiring Items", className="metric-label"),
                            html.Div([
                                html.H3(id="expiring-items-value", className="metric-value"),
                                html.Span(id="expiring-items-change", className="metric-change")
                            ], className="d-flex align-items-center"),
                        ],
                        className="metric-card"
                    ),
                    md=4
                ),
            ],
            className="mb-4"
        ),
        html.H4("Quick Actions", className="section-title"),
        html.Div(
            [
                dbc.Button("Manage Stock", className="quick-action-btn active"),
                dbc.Button("Restocking", className="quick-action-btn"),
                dbc.Button("Analysis", className="quick-action-btn"),
            ],
            className="quick-actions-container mb-4"
        ),

        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("Analytics Preview", className="card-title"),
                            html.P("Sales Over Time", className='small-text mb-1'),
                            html.P(id='sales-over-time-summary', className='text-success mb-2'),
                            dcc.Graph(
                                id='sales-over-time-chart',
                                config={'displayModeBar': False},
                                style={'height': '200px'}
                            )
                        ],
                        className="analytics-card"
                    ),
                    lg=6
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("Notifications & Alerts", className="card-title"),
                            html.Div(id="notifications-list", className="notifications-list")
                        ],
                        className="analytics-card notifications-panel"
                    ),
                    lg=6
                ),
            ],
            className="mb-4"
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("Top Categories in Profit", className="card-title"),
                            html.P("Current Quarter", id="profit-period-summary", className="text-muted small-text mb-1"),
                            html.H3(id="total-profit-value", className="profit-value mb-3"),
                            html.Div(id="category-profit-bars-container", className="category-profit-bars")
                        ],
                        className="analytics-card"
                    ),
                    lg=6
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("Sustainability Insights", className="card-title"),
                            html.P("Monthly Waste Breakdown", className="small-text mb-1"), # Clarified for chart
                            html.H3(id='total-waste-kgs', className='waste-main-value mb-2'),
                            html.P(id='monthly-waste-change-summary', className='waste-value small-text mb-3'),
                            dcc.Graph(
                                id='monthly-waste-chart',
                                config={'displayModeBar': False},
                                style={'height': '150px'}
                            )
                        ],
                        className="analytics-card"
                    ),
                    lg=6
                ),
            ],
            className="mb-4"
        ),
    ],
    className="content"
)


# Expiry Management Page Content
expiry_management_content = html.Div(
    [
        html.Div(
            [
                html.H3("Expiry Management", className="dashboard-header-title"),
                html.P("Track and manage products approaching their expiry dates.", className="text-muted"),
                html.Img(src="/assets/user_avatar.png", className="user-avatar")
            ],
            className="dashboard-header"
        ),
        dbc.Card(
            [
                html.Div(
                    [
                        html.H5("Items Nearing Expiration", className="card-title"),
                        html.Div(
                            [
                                html.Span("View: ", className="me-2"),
                                dcc.Dropdown(
                                    id='expiry-view-dropdown',
                                    options=[
                                        {'label': 'All', 'value': 'All'},
                                        {'label': 'Expiring Soon', 'value': 'Expiring Soon'},
                                        {'label': 'Expired', 'value': 'Expired'}
                                    ],
                                    value='All',
                                    clearable=False,
                                    style={'width': '150px', 'display': 'inline-block', 'verticalAlign': 'middle'}
                                )
                            ],
                            className="d-flex align-items-center justify-content-end mb-3"
                        ),
                        dash_table.DataTable(
                            id='expiry-table',
                            columns=[
                                    {"name": "PRODUCT NAME", "id": "PRODUCT NAME"},
                                    {"name": "STOCK ID", "id": "STOCK ID"},
                                    {"name": "QUANTITY", "id": "QUANTITY"},
                                    {"name": "EXPIRY DATE", "id": "EXPIRY DATE"},
                                    {"name": "STATUS", "id": "STATUS"},
                                    # THIS IS CRUCIAL: 'presentation': 'markdown'
                                     {"name": "ACTIONS", "id": "ACTIONS"}
                                     
                                ],
                            data=[],
    editable=False, 
    cell_selectable=True, # <<< Enable individual cell selection
    
    page_action='native',
    page_size=10,  # Set this to your desired number of rows (e.g., 10, 15, 20)
    
                            style_table={'overflowX': 'auto', 'minWidth': '100%'},
                            style_header={
                                'backgroundColor': '#f8f9fa',
                                'fontWeight': 'bold',
                                'textAlign': 'left',
                                'borderBottom': '2px solid #e0e0e0',
                                'padding': '12px 15px'
                            },
                            style_data={
                                'whiteSpace': 'normal',
                                'height': 'auto',
                                'textAlign': 'left',
                                'padding': '10px 15px',
                                'borderBottom': '1px solid #e0e0e0'
                            },
                            style_cell={
                                'fontFamily': 'Inter, sans-serif',
                                'fontSize': '14px',
                                'color': '#333'
                            },
                             style_data_conditional=[
                {
                    'if': {
                        'filter_query': '{STATUS} = "Expired"',
                        'column_id': 'STATUS'
                    },
                    'backgroundColor': '#dc3545', # Red color for Expired
                    'color': 'white'
                },
                {
                    'if': {
                        'filter_query': '{STATUS} = "Expiring Soon"',
                        'column_id': 'STATUS'
                    },
                    'backgroundColor': '#ffc107', # Yellow/Orange color for Expiring Soon
                    'color': '#343a40'
                },
                { # Rule for 'Nearing Expiry (X Days)' - 
                    'if': {
                        'filter_query': '{STATUS} contains "Nearing Expiry (" && {STATUS} contains " Days)"',
                        'column_id': 'STATUS'
                    },
                    'backgroundColor': '#ffc107', 
                    'color': '#343a40' 
                },
                { 
                    'if': {
                        'filter_query': '{STATUS} = "Good"',
                        'column_id': 'STATUS'
                    },
                    'color': '#27ae60', # Green color for Good
                    'fontWeight': 'bold'
                }
            ],
                            selected_rows=[],
                            css=[
                                {"selector": ".dash-spreadsheet-top-container", "rule": "display:none"}, # Hide default pagination/filter bar if not needed
                                {"selector": ".dash-fixed-content", "rule": "width: 100%;"},
                                {"selector": ".dash-table-container .row", "rule": "margin: 0; flex-wrap: nowrap;"},
                                {"selector": ".dash-table-container .col-md-12", "rule": "width:100%; padding:0;"},
                            ]
                        ),
                        html.Button(
                            [html.I(className="bi bi-plus-circle me-2"), "Add New Item Batch"],
                            id='add-item-batch-button',
                            className='add-item-batch-button mt-4'
                        )
                    ]
                ),
            ],
            className="analytics-card mb-4" # Re-using analytics-card style
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("Expiry Overview", className="card-title"),
                            html.Div(
                                [
                                    html.P("Expired Items:", className="expiry-overview-label"),
                                    html.P(id="expired-items-count", className="expiry-overview-value text-danger"),
                                ], className="expiry-overview-item"
                            ),
                            html.Div(
                                [
                                    html.P("Expiring in 7 Days:", className="expiry-overview-label"),
                                    html.P(id="expiring-7-days-count", className="expiry-overview-value text-warning"),
                                ], className="expiry-overview-item"
                            ),
                            html.Div(
                                [
                                    html.P("Expiring in 30 Days:", className="expiry-overview-label"),
                                    html.P(id="expiring-30-days-count", className="expiry-overview-value text-info"),
                                ], className="expiry-overview-item"
                            ),
                        ],
                        className="analytics-card"
                    ),
                    lg=6
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            html.H5("Quick Actions", className="card-title"),
                            dbc.Button("Generate Expiry Report", id="generate-expiry-report-btn", className="quick-action-btn-expiry"),
                            dbc.Button("Set Notifications", id="set-notifications-btn", className="quick-action-btn-expiry"),
                        ],
                        className="analytics-card d-flex flex-column justify-content-start"
                    ),
                    lg=6
                ),
            ],
            className="mb-4"
        ),
    ],
    className="content"
)


# Main App Layout
app.layout = html.Div([
    dcc.Store(id='stored-data', data=app_data),
    dcc.Location(id='url', refresh=False),
    sidebar,
    html.Div(id='page-content', className="content-container") # This will hold the dynamic content
], className="app-container")


# --- Callbacks ---

@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/expiry-management':
        return expiry_management_content
    elif pathname == '/':
        return dashboard_content
    elif pathname == '/stock-management': # <--- ADD THIS LINE
        return stock_management_content # <--- ADD THIS LINE
    # Add more conditions for other pages as they are created
    return html.Div([html.H1("404: Not found"), html.P(f"The pathname {pathname} was not recognised...")])


@app.callback(
    [
        Output('items-in-stock-value', 'children'),
        Output('items-in-stock-change', 'children'),
        Output('items-in-stock-change', 'className'),
        Output('reorder-recommendations-value', 'children'),
        Output('reorder-recommendations-change', 'children'),
        Output('reorder-recommendations-change', 'className'),
        Output('expiring-items-value', 'children'),
        Output('expiring-items-change', 'children'),
        Output('expiring-items-change', 'className'),
    ],
    Input('stored-data', 'data')
)
def update_realtime_metrics(data):
    metrics = get_realtime_metrics(data)
    stock_class = f"metric-change {metrics['stock_change_class']}"
    reorder_class = f"metric-change {metrics['reorder_change_class']}"
    expiring_class = f"metric-change {metrics['expiring_change_class']}"
    return (
        metrics['items_in_stock'], html.Span([html.I(className="bi bi-arrow-up-right"), metrics['stock_change']]), stock_class,
        metrics['reorder_recommendations'], html.Span([html.I(className="bi bi-arrow-up-right"), metrics['reorder_change']]), reorder_class,
        html.Span(metrics['expiring_items']), html.Span([html.I(className="bi bi-arrow-down-right"), metrics['expiring_change']]), expiring_class
    )

@app.callback(
    [Output('sales-over-time-chart', 'figure'),
     Output('sales-over-time-summary', 'children')],
    [Input('stored-data', 'data')]
)
def update_sales_chart(data):
    monthly_sales = get_sales_data_for_chart(data)
    total_sales_str, percentage_change_str = calculate_last_5_months_sales_change(data)

    if monthly_sales.empty:
        fig = go.Figure()
    else:
        fig = px.line(monthly_sales, x='SaleDate', y='TotalPrice', markers=True,
                      line_shape='linear',
                      color_discrete_sequence=['#1abc9c'])

        fig.update_xaxes(
            tickvals=monthly_sales['SaleDate'],
            ticktext=monthly_sales['SaleDate'].dt.strftime('%b'),
            showgrid=False, showline=False, zeroline=False
        )
        fig.update_yaxes(
            showgrid=True, gridcolor='#e0e0e0', showline=False, zeroline=False, showticklabels=True
        )

    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor='white', paper_bgcolor='white',
        xaxis_title=None, yaxis_title=None,
        hovermode='x unified', font=dict(family="Inter, sans-serif")
    )
    summary_text = f"₹{total_sales_str} Last 5 Months {percentage_change_str}"
    return fig, summary_text

@app.callback(
    [Output('total-profit-value', 'children'),
     Output('category-profit-bars-container', 'children')],
    [Input('stored-data', 'data')]
)
def update_profit_categories(data):
    category_profit, total_profit = get_top_categories_in_profit(data)
    total_profit_formatted = f"₹{total_profit:,.0f}"
    bars_children = []

    # Check if category_profit DataFrame is empty or contains only zero profit
    if category_profit.empty or total_profit == 0:
        bars_children.append(
            html.Div(
                "No profit data available for the current quarter or categories.",
                style={'textAlign': 'center', 'padding': '20px', 'color': '#888'}
            )
        )
        total_profit_formatted = "₹0" # Ensure total profit also shows zero
    else:
        max_profit = category_profit['Profit'].max()
        # Ensure max_profit is not zero to avoid division by zero
        max_profit = max_profit if max_profit > 0 else 1 

        for index, row in category_profit.iterrows():
            percentage = (row['Profit'] / max_profit) * 100
            bars_children.append(
                html.Div(className='category-bar-item', children=[
                    html.Span(row['Category'], className='category-name'),
                    html.Span(f"₹{row['Profit']:,.0f}", className='category-value'),
                    html.Div(className='category-bar-background', children=[
                        html.Div(className='category-bar-fill', style={'width': f'{percentage}%'})
                    ])
                ])
            )
    return total_profit_formatted, bars_children

@app.callback(
    Output('notifications-list', 'children'),
    Input('stored-data', 'data')
)
def update_notifications(data):
    notifications = get_notifications(data)
    notification_elements = []
    for notification in notifications:
        icon_class = ""
        if notification['type'] == 'expiring':
            icon_class = "bi bi-exclamation-triangle-fill text-warning"
        elif notification['type'] == 'new_supplier':
            icon_class = "bi bi-person-plus-fill text-info"
        elif notification['type'] == 'waste':
            icon_class = "bi bi-trash-fill text-success"
        elif notification['type'] == 'low_stock':
            icon_class = "bi bi-box-fill text-danger"
        elif notification['type'] == 'pending_invoice':
            icon_class = "bi bi-file-earmark-text text-warning"
        notification_elements.append(
            html.Div(
                [
                    html.Div([html.I(className=f"notification-icon {icon_class}"), html.Span(notification['text'], className="notification-text")]),
                    html.Span(notification['time'], className="notification-time")
                ],
                className="notification-item"
            )
        )
    return notification_elements

@app.callback(
    [Output('monthly-waste-chart', 'figure'),
     Output('total-waste-kgs', 'children'),
     Output('monthly-waste-change-summary', 'children')],
    [Input('stored-data', 'data')]
)
def update_sustainability_insights(data):
    # Get overall quarterly waste for the summary text
    overall_waste_summary = calculate_overall_quarterly_waste(data) # Calling the new quarterly function
    total_waste_text = overall_waste_summary['total_waste_text']
    waste_change_text = overall_waste_summary['change_text']

    # Get monthly waste data for the bar chart (last 3 months for the quarter)
    monthly_data_for_chart = get_monthly_waste_data_for_chart(data, num_months=3) # Requesting 3 months for the chart
    waste_df_monthly = monthly_data_for_chart['df']

    if waste_df_monthly.empty:
        fig = go.Figure()
    else:
        fig = px.bar(waste_df_monthly, x='Month', y='Waste_KGS', # 'Month' column contains 'Feb', 'Mar', etc.
                     color_discrete_sequence=['#a0d9b4'])

        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            plot_bgcolor='white', paper_bgcolor='white',
            xaxis_title=None, yaxis_title=None,
            xaxis=dict(showgrid=False, showline=False, zeroline=False),
            yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=False),
            hovermode='x unified', font=dict(family="Inter, sans-serif")
        )
        fig.update_traces(marker_line_width=0)

    # The summary text now indicates "Last Quarter"
    return fig, total_waste_text, f"Last Quarter {waste_change_text}"


# Callbacks for Expiry Management Page
@app.callback(
    [Output('expiry-table', 'data'),
     Output('expired-items-count', 'children'),
     Output('expiring-7-days-count', 'children'),
     Output('expiring-30-days-count', 'children')],
    [Input('stored-data', 'data'),
     Input('expiry-view-dropdown', 'value')]
)
def update_expiry_data(data, view_filter):
    table_data_df, expiry_overview_metrics = get_expiry_data(data, view_filter)

    # Convert DataFrame to a list of dictionaries (records)
    records = table_data_df.to_dict('records')

    # --- SIMPLIFIED ACTIONS COLUMN: Just a string for the cell ---
    for row in records:
        # We can put a string that guides the user to click for actions
        row['ACTIONS'] = "Discount | Dispose"
    
    return (
        records,
        expiry_overview_metrics['expired'],
        expiry_overview_metrics['expiring_7'],
        expiry_overview_metrics['expiring_30']
    )
    
   # --- Callback to handle cell clicks (modified slightly for clarity) ---
@app.callback(
    Output('some-output-div', 'children'), # Make sure this div exists in your layout
    Input('expiry-table', 'active_cell'),
    State('expiry-table', 'data')
)
def handle_action_cell_click(active_cell, table_data):
    print("Active Cell:", active_cell) # Keep this for debugging in your terminal
    if active_cell:
        row_id = active_cell['row']
        column_id = active_cell['column_id']
        # The value will be "[Discount](javascript:void(0)) | [Dispose](javascript:void(0))"

        if column_id == 'ACTIONS':
            clicked_row_data = table_data[row_id]
            stock_id = clicked_row_data['STOCK ID']

            
            return html.Div([
                html.P(f"Action requested for Stock ID: {stock_id}."),
                html.P("What action do you want to perform?"),
                dbc.Button("Discount This Item", id={'type': 'final-action-btn', 'action': 'discount', 'stock_id': stock_id}, color="success", className="me-2"),
                dbc.Button("Dispose This Item", id={'type': 'final-action-btn', 'action': 'dispose', 'stock_id': stock_id}, color="danger")
            ])
            
    return ""

# --- Stock Management Page Content ---
stock_management_content = html.Div(
    [
        html.Div(
            [
                html.H3("Stock Management", className="dashboard-header-title"),
                html.P("Manage your stock levels, add new items, and update existing items. All weight-based units are in kilograms (kgs).", className="text-muted"),
                html.Img(src="/assets/user_avatar.png", className="user-avatar")
            ],
            className="dashboard-header"
        ),
        dbc.Card(
            [
                html.Div(
                    [
                        dbc.Button(
                            [html.I(className="bi bi-upload me-2"), "Upload Data"],
                            id="upload-data-btn",
                            className="upload-data-btn mb-4"
                        ),
                        # Search Bar
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText(html.I(className="bi bi-search")),
                                dbc.Input(id="stock-search-input", placeholder="Search for items by name, SKU, or supplier...", type="text", className="search-input")
                            ],
                            className="mb-4"
                        ),
                        # Filter Dropdowns
                        dbc.Row(
                            [
                                dbc.Col(
                                    dcc.Dropdown(
                                        id='stock-category-filter',
                                        options=[{'label': 'All Categories', 'value': 'all'}],
                                        value='all',
                                        placeholder="Category",
                                        clearable=False,
                                        className="filter-dropdown"
                                    ),
                                    md=4
                                ),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id='stock-supplier-filter',
                                        options=[{'label': 'All Suppliers', 'value': 'all'}],
                                        value='all',
                                        placeholder="Supplier",
                                        clearable=False,
                                        className="filter-dropdown"
                                    ),
                                    md=4
                                ),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id='stock-status-filter',
                                        options=[
                                            {'label': 'All Statuses', 'value': 'all'},
                                            {'label': 'In Stock', 'value': 'In Stock'},
                                            {'label': 'Low Stock', 'value': 'Low Stock'},
                                            {'label': 'Out of Stock', 'value': 'Out of Stock'}
                                        ],
                                        value='all',
                                        placeholder="Status",
                                        clearable=False,
                                        className="filter-dropdown"
                                    ),
                                    md=4
                                ),
                            ],
                            className="mb-4"
                        ),
                        # Stock Table
                        dash_table.DataTable(
                            id='stock-table',
                            columns=[
                                {"name": "ITEM NAME", "id": "ITEM NAME"},
                                {"name": "QUANTITY", "id": "QUANTITY"},
                                {"name": "SUPPLIER", "id": "SUPPLIER"},
                                {"name": "CATEGORY", "id": "CATEGORY"},
                                {"name": "STATUS", "id": "STATUS"},
                                {"name": "ACTIONS", "id": "ACTIONS", "presentation": "markdown"},
                                
                            ],

                            data=[],
                            editable=False,
                            page_action='native',
                            page_size=10,
                            sort_action="native",
                            filter_action="none",
                            markdown_options={"html": True},
                            style_table={'overflowX': 'auto', 'minWidth': '100%'},
                            style_header={
                                'backgroundColor': '#f8f9fa',
                                'fontWeight': 'bold',
                                'textAlign': 'left',
                                'borderBottom': '2px solid #e0e0e0',
                                'padding': '12px 15px'
                            },
                            style_data={
                                'whiteSpace': 'normal',
                                'height': 'auto',
                                'textAlign': 'left',
                                'padding': '10px 15px',
                                'borderBottom': '1px solid #e0e0e0'
                            },
                            style_cell={
                                'fontFamily': 'Inter, sans-serif',
                                'fontSize': '14px',
                                'color': '#333'
                            },
                            style_data_conditional=[
                                {
                                    'if': {'column_id': 'STATUS', 'filter_query': '{STATUS} = "In Stock"'},
                                    'color': '#27ae60',
                                    'fontWeight': 'bold'
                                },
                                {
                                    'if': {'column_id': 'STATUS', 'filter_query': '{STATUS} = "Low Stock"'},
                                    'color': '#f39c12',
                                    'fontWeight': 'bold'
                                },
                                {
                                    'if': {'column_id': 'STATUS', 'filter_query': '{STATUS} = "Out of Stock"'},
                                    'color': '#e74c3c',
                                    'fontWeight': 'bold'
                                },
                                {
                                    'if': {'column_id': 'ACTIONS'},
                                    'textAlign': 'center',
                                    'padding': '0',
                                },
                            ],
                            css=[
                                {"selector": ".dash-spreadsheet-top-container", "rule": "display:none"},
                                {"selector": ".dash-fixed-content", "rule": "width: 100%;"},
                                {"selector": ".dash-table-container .row", "rule": "margin: 0; flex-wrap: nowrap;"},
                                {"selector": ".dash-table-container .col-md-12", "rule": "width:100%; padding:0;"},
                            ]
                        )
                    ]
                )
            ],
            className="analytics-card mb-4"
        ),
        # --- NEW MODAL FOR STOCK PRODUCT DETAILS ---
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Product Details")),
                dbc.ModalBody(id="stock-product-details-body"), # Content will go here
                dbc.ModalFooter(
                    dbc.Button(
                        "Close", id="close-stock-details-modal", className="ms-auto", n_clicks=0
                    )
                ),
            ],
            id="stock-details-modal",
            is_open=False, # Hidden by default
            size="lg",
            centered=True,
        ),
        # --- END NEW MODAL ---
    ],
    className="content"
)


# --- Helper Function for Stock Management Data ---
def get_stock_data(stored_data_json, search_term='', category_filter='all', supplier_filter='all', status_filter='all'):
    df_products = pd.read_json(io.StringIO(stored_data_json['products']), orient='split') if stored_data_json.get('products') else pd.DataFrame()

    if df_products.empty:
        print("df_products is empty in get_stock_data.")
        return pd.DataFrame().to_dict('records')

    # Ensure 'ProductID' is available early
    if 'ProductID' not in df_products.columns:
        print("Warning: 'ProductID' column not found, 'STOCK ID' cannot be generated. Returning empty.")
        return pd.DataFrame().to_dict('records')

    # Ensure 'quantity' is numeric (important for calculations and comparisons)
    if 'quantity' in df_products.columns:
        df_products['quantity'] = pd.to_numeric(df_products['quantity'], errors='coerce').fillna(0)
    else:
        print("Warning: 'quantity' column not found in df_products. Returning empty.")
        return pd.DataFrame().to_dict('records')

    # Ensure 'SupplierName' is renamed to 'Supplier' if coming directly from CSV
    # This part should ideally be in load_data(), but adding here as a safeguard if not.
    if 'SupplierName' in df_products.columns and 'Supplier' not in df_products.columns:
        df_products = df_products.rename(columns={'SupplierName': 'Supplier'})
    elif 'Supplier' not in df_products.columns:
        print("Warning: Neither 'SupplierName' nor 'Supplier' column found. Returning empty.")
        return pd.DataFrame().to_dict('records')

    # --- Calculate Stock Status ---
    LOW_STOCK_THRESHOLD = 20
    OUT_OF_STOCK_THRESHOLD = 0

    df_products['STATUS'] = 'In Stock' # Default status
    df_products.loc[df_products['quantity'] <= OUT_OF_STOCK_THRESHOLD, 'STATUS'] = 'Out of Stock'
    df_products.loc[(df_products['quantity'] > OUT_OF_STOCK_THRESHOLD) & (df_products['quantity'] <= LOW_STOCK_THRESHOLD), 'STATUS'] = 'Low Stock'
    
    # --- Add ACTIONS column (Must be a Markdown string for DataTable rendering) ---
    # This markdown string will render as a clickable link.
    df_products['ACTIONS'] = "View" # Corrected to Markdown link

    # --- Apply Filters ---
    # IMPORTANT: filtered_df must be created *after* all necessary columns (like STATUS, ACTIONS) are added to df_products
    filtered_df = df_products.copy()

    # Search by Item Name, Product ID (SKU), Supplier
    if search_term:
        search_term_lower = search_term.lower()
        filtered_df = filtered_df[
            filtered_df['ProductName'].str.lower().str.contains(search_term_lower, na=False) |
            filtered_df['ProductID'].astype(str).str.lower().str.contains(search_term_lower, na=False) |
            filtered_df['Supplier'].str.lower().str.contains(search_term_lower, na=False)
        ]

    # Category Filter
    if category_filter != 'all':
        filtered_df = filtered_df[filtered_df['Category'] == category_filter]

    # Supplier Filter
    if supplier_filter != 'all':
        filtered_df = filtered_df[filtered_df['Supplier'] == supplier_filter]

    # Status Filter
    if status_filter != 'all':
        filtered_df = filtered_df[filtered_df['STATUS'] == status_filter]
    
    # --- Combine Quantity with UnitOfMeasure for display (Moved to after filtering) ---
    # Ensure 'Weight' column exists if needed elsewhere (from previous discussions)
    if 'Weight' not in filtered_df.columns:
        filtered_df['Weight'] = 0.5 # Default weight if not present

    if 'quantity' in filtered_df.columns and 'UnitOfMeasure' in filtered_df.columns:
        filtered_df['DISPLAY_QUANTITY'] = filtered_df['quantity'].astype(str) + ' ' + filtered_df['UnitOfMeasure']
    else:
        filtered_df['DISPLAY_QUANTITY'] = filtered_df['quantity'].astype(str)
        print("Warning: 'UnitOfMeasure' column not found in filtered_df, displaying quantity without units.")
        
        
    
    # --- Prepare data for the table ---
    # Define the required columns for the final DataTable display
    required_cols_for_display = [
        'ProductID', # Included for use in the modal callback via 'STOCK ID'
        'ProductName',
        'DISPLAY_QUANTITY', # Use the new combined quantity + unit column
        'Supplier',
        'Category',
        'STATUS',
        'ACTIONS'
    ]

    # Perform a check if all required columns are present in filtered_df before selection
    for col in required_cols_for_display:
        if col not in filtered_df.columns:
            print(f"Error: Required column '{col}' not found in filtered_df for table display. Returning empty.")
            return pd.DataFrame().to_dict('records')

    # Select and rename columns for DataTable output
    table_data = filtered_df[required_cols_for_display].rename(columns={
        'ProductID': 'STOCK ID', # Renamed for display and internal use (e.g., in modal)
        'ProductName': 'ITEM NAME',
        'DISPLAY_QUANTITY': 'QUANTITY', # Renamed heading to just 'QUANTITY'
        'Supplier': 'SUPPLIER',
        'Category': 'CATEGORY',
    })

    return table_data.to_dict('records') # Return as list of dictionaries

# --- Callbacks for Stock Management Page ---
@app.callback(
    [Output('stock-table', 'data'),
     Output('stock-category-filter', 'options'),
     Output('stock-supplier-filter', 'options')],
    [Input('stored-data', 'data'),
     Input('stock-search-input', 'value'),
     Input('stock-category-filter', 'value'),
     Input('stock-supplier-filter', 'value'),
     Input('stock-status-filter', 'value')]
)
def update_stock_table(data, search_term, category_filter, supplier_filter, status_filter):
    # Get data for the table based on filters
    filtered_stock_data = get_stock_data(data, search_term, category_filter, supplier_filter, status_filter)

    # Get unique categories and suppliers for dropdown options
    df_products = pd.read_json(io.StringIO(data['products']), orient='split') if data.get('products') else pd.DataFrame()
    
    categories = [{'label': 'All Categories', 'value': 'all'}]
    if not df_products.empty and 'Category' in df_products.columns:
        categories.extend([{'label': cat, 'value': cat} for cat in df_products['Category'].unique()])

    suppliers = [{'label': 'All Suppliers', 'value': 'all'}]
    if not df_products.empty and 'Supplier' in df_products.columns:
        suppliers.extend([{'label': sup, 'value': sup} for sup in df_products['Supplier'].unique()])
    
    return filtered_stock_data, categories, suppliers

# --- Callback for 'View' button in Stock Table (using active_cell) ---
@app.callback(
    [Output('stock-details-modal', 'is_open'),
     Output('stock-product-details-body', 'children')],
    [Input('stock-table', 'active_cell'), # <--- CHANGED: Listen to active_cell of the DataTable
     Input('close-stock-details-modal', 'n_clicks')], # Input for closing the modal
    [State('stock-table', 'data'),         # <--- ADDED: State to access the full table data
     State('stock-details-modal', 'is_open')],
    prevent_initial_call=True
)
def toggle_stock_details_modal(active_cell, close_n_clicks, table_data, is_open): # <--- UPDATED ARGUMENTS
    ctx = dash.callback_context

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id']

    # Handle close button click
    if "close-stock-details-modal" in trigger_id and close_n_clicks:
        return False, dash.no_update # Close modal, no update to body

    # Handle active_cell click on the table
    # Check if the trigger was from 'stock-table.active_cell' and if a cell was actually clicked
    if "stock-table.active_cell" in trigger_id and active_cell:
        row_index = active_cell['row']
        column_id = active_cell['column_id']

        # Only proceed if the clicked column is 'ACTIONS'
        if column_id == 'ACTIONS':
            clicked_row_data = table_data[row_index] # Get the data for the clicked row
            stock_id = clicked_row_data.get('STOCK ID', 'N/A') # Get the stock ID from the row data

            # Basic Information
            item_name = clicked_row_data.get('ITEM NAME', 'N/A') # Mapped from ProductName
            category = clicked_row_data.get('CATEGORY', 'N/A')
            supplier_name = clicked_row_data.get('SUPPLIER', 'N/A') # Mapped from SupplierName

            # Get raw numeric quantity and unit of measure for calculations and separate display
            raw_quantity = clicked_row_data.get('StockQuantity', 'N/A')
            unit_of_measure = clicked_row_data.get('UnitOfMeasure', 'N/A')

            # Price and Profitability
            cost_price = clicked_row_data.get('Cost', 'N/A')
            selling_price = clicked_row_data.get('Price', 'N/A')

            # Inventory Details
            minimum_stock = clicked_row_data.get('ReorderPoint', 'N/A')
            last_restocked = 'N/A' # Not in CSV - will be N/A

            # Supplier contact
            phone = 'N/A' # Not in CSV - will be N/A
            email = 'N/A' # Not in CSV - will be N/A

            # --- Calculations for Price and Profitability ---
            profit_margin = 'N/A'
            total_cost_value = 'N/A'
            expected_revenue = 'N/A'
            estimated_profit = 'N/A'

            try:
                numeric_cost = float(cost_price)
                numeric_selling = float(selling_price)
                numeric_quantity = float(raw_quantity)

                if numeric_selling != 0:
                    profit_margin = f"{((numeric_selling - numeric_cost) / numeric_selling) * 100:.2f}%"
                
                total_cost_value = f"₹{numeric_cost * numeric_quantity:.2f}"
                expected_revenue = f"₹{numeric_selling * numeric_quantity:.2f}"
                estimated_profit = f"₹{(numeric_selling - numeric_cost) * numeric_quantity:.2f}"

            except (ValueError, TypeError):
                # If any of the values are not numeric, calculations will remain N/A
                pass

            # --- Construct the modal content based on your detailed list ---
            details_content = html.Div([
                html.H4("Product Details", className="mb-3"), # Main modal title

                # Basic Information
                html.H5("Basic Information", className="mb-2 mt-4"),
                dbc.Row([
                    dbc.Col(html.P(f"Item Name: {item_name}"), width=6),
                    dbc.Col(html.P(f"Category: {category}"), width=6),
                ]),
                dbc.Row([
                    dbc.Col(html.P(f"Supplier: {supplier_name}"), width=6),
                    dbc.Col(html.P(f"Quantity: {raw_quantity} {unit_of_measure}"), width=6), # Displaying numeric quantity with unit
                ]),

                # Price and Profitability
                html.H5("Price and Profitability", className="mb-2 mt-4"),
                dbc.Row([
                    dbc.Col(html.P(f"Cost price: ₹{cost_price}"), width=6),
                    dbc.Col(html.P(f"Selling price: ₹{selling_price}"), width=6),
                ]),
                dbc.Row([
                    dbc.Col(html.P(f"Profit Margin: {profit_margin}"), width=6),
                    dbc.Col(html.P(f"Total cost value: {total_cost_value}"), width=6),
                ]),
                dbc.Row([
                    dbc.Col(html.P(f"Expected revenue: {expected_revenue}"), width=6),
                    dbc.Col(html.P(f"Estimated profit: {estimated_profit}"), width=6),
                ]),

                # Inventory Details
                html.H5("Inventory Details", className="mb-2 mt-4"),
                dbc.Row([
                    dbc.Col(html.P(f"Unit type: {unit_of_measure}"), width=6),
                    dbc.Col(html.P(f"Minimum stock: {minimum_stock}"), width=6),
                ]),
                dbc.Row([
                    dbc.Col(html.P(f"Total quantity: {raw_quantity} {unit_of_measure}"), width=6), # Assuming this is current stock again
                    dbc.Col(html.P(f"Last Restocked: {last_restocked}"), width=6),
                ]),

                # Supplier Contact
                html.H5("Supplier Contact", className="mb-2 mt-4"),
                dbc.Row([
                    dbc.Col(html.P(f"Phone: {phone}"), width=6),
                    dbc.Col(html.P(f"Email: {email}"), width=6),
                ]),
            ])
            # --- End of new modal content construction ---

            return not is_open, details_content
    
    # If no relevant trigger or active_cell is None, prevent update.
    return is_open, dash.no_update


if __name__ == '__main__':
    app.run(debug=True)