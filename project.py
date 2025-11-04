import sqlite3
import os
import pandas as pd  # <-- Added
import numpy as np   # <-- Added

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def setup_database():
    """
    Connects to the SQLite database and creates the 'customers' table 
    if it doesn't already exist.
    """
    conn = sqlite3.connect('utility.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        monthly_usage_kwh REAL DEFAULT 0.0,
        bill_paid BOOLEAN DEFAULT 0 
    )
    ''')
    
    conn.commit()
    conn.close()

def admin_add_customer():
    """Admin function: Adds a new customer to the database."""
    print("--- Add New Customer ---")
    try:
        name = input("Enter full name: ")
        email = input("Enter email: ")
        usage = float(input("Enter initial monthly usage (kWh): "))
        
        conn = sqlite3.connect('utility.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO customers (full_name, email, monthly_usage_kwh) VALUES (?, ?, ?)",
            (name, email, usage)
        )
        
        conn.commit()
        conn.close()
        
        print(f"\n[Success] Customer '{name}' added.")
    except sqlite3.IntegrityError:
        print(f"\n[Error] Email '{email}' already exists.")
    except ValueError:
        print("\n[Error] Invalid usage. Please enter a number.")
    
    input("\nPress Enter to return to the admin menu...")

def admin_view_all_customers():
    """Admin function: Reads and displays all customer records."""
    print("--- View All Customers ---")
    conn = sqlite3.connect('utility.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM customers ORDER BY full_name")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("No customers found in the database.")
    else:
        print(f"{'ID':<5} | {'Name':<25} | {'Email':<25} | {'Usage (kWh)':<15} | {'Bill Paid':<10}")
        print("-" * 85)
        for row in rows:
            paid_status = "Yes" if row[4] else "No"
            print(f"{row[0]:<5} | {row[1]:<25} | {row[2]:<25} | {row[3]:<15.2f} | {paid_status:<10}")
            
    input("\nPress Enter to return to the admin menu...")

def admin_bulk_load():
    """Admin function: Loads new customers from a CSV file using pandas."""
    print("--- Bulk Load Customers from CSV ---")
    
    # Note: We imported pandas at the top of the file
    
    filename = input("Enter the CSV filename (e.g., sample_customers.csv): ")
    
    try:
        # 1. Use pandas to read the CSV into a DataFrame
        df = pd.read_csv(filename)
        
        # Check for required columns
        if not {'full_name', 'email', 'monthly_usage_kwh'}.issubset(df.columns):
            print("[Error] CSV must contain 'full_name', 'email', and 'monthly_usage_kwh' columns.")
            input("\nPress Enter to return...")
            return

        # 2. Connect to the database
        conn = sqlite3.connect('utility.db')
        
        # 3. Use the DataFrame's .to_sql() method to append data
        df.to_sql('customers', conn, if_exists='append', index=False)
        
        conn.close()
        
        print(f"\n[Success] Successfully added {len(df)} new customers from {filename}.")
        
    except FileNotFoundError:
        print(f"\n[Error] File not found: {filename}")
    except pd.errors.EmptyDataError:
        print(f"\n[Error] File {filename} is empty.")
    except sqlite3.IntegrityError as e:
        print(f"\n[Error] Database error. One or more emails might already exist. ({e})")
    except Exception as e:
        print(f"\n[Error] An unexpected error occurred: {e}")

    input("\nPress Enter to return to the admin menu...")

def admin_view_analytics():
    """Admin function: Views consumption and billing analytics."""
    print("--- Portal Analytics Dashboard ---")
    
    # Note: We imported pandas and numpy at the top of the file
        
    conn = sqlite3.connect('utility.db')
    
    # 1. Use pandas to read the entire SQL table into a DataFrame
    try:
        df = pd.read_sql_query("SELECT * FROM customers", conn)
    except pd.errors.DatabaseError:
        print("\n[Error] Could not read database. Is it empty?")
        conn.close()
        input("\nPress Enter to return...")
        return
        
    conn.close()

    if df.empty:
        print("\nNo customer data to analyze.")
        input("\nPress Enter to return...")
        return

    # 2. Use pandas for basic statistics
    total_customers = len(df)
    avg_usage = df['monthly_usage_kwh'].mean()
    max_usage = df['monthly_usage_kwh'].max()
    max_user = df[df['monthly_usage_kwh'] == max_usage]['full_name'].values[0]

    # Calculate billing
    COST_PER_KWH = 0.12
    df['amount_due'] = df['monthly_usage_kwh'] * COST_PER_KWH
    
    total_revenue = df['amount_due'].sum()
    unpaid_bills_df = df[df['bill_paid'] == 0]
    total_unpaid = unpaid_bills_df['amount_due'].sum()
    
    # 3. Use numpy for a specific calculation
    # Get the 'amount_due' column as a NumPy array
    amount_due_array = df['amount_due'].values 
    
    # Use a fast, vectorized numpy operation
    hypothetical_revenue = np.sum(amount_due_array * 1.05)
    
    # Display the report
    print("\n--- Customer & Usage Stats ---")
    print(f"  Total Customers:   {total_customers}")
    print(f"  Average Usage:     {avg_usage:.2f} kWh")
    print(f"  Highest Consumer:  {max_user} at {max_usage:.2f} kWh")
    
    print("\n--- Billing Stats ---")
    print(f"  Total Billed:      ${total_revenue:.2f}")
    print(f"  Total Unpaid:      ${total_unpaid:.2f} ({len(unpaid_bills_df)} customers)")
    
    print("\n--- Projections (using NumPy) ---")
    print(f"  Total revenue with 5% price hike: ${hypothetical_revenue:.2f}")
    
    input("\nPress Enter to return to the admin menu...")

def admin_menu():
    """Displays the admin-specific menu and handles choices."""
    while True:
        clear_screen()
        print("--- Admin Management Portal ---")
        print("1. Add New Customer (Create)")
        print("2. View All Customers (Read)")
        print("3. Bulk Load Customers from CSV (Pandas)") # <-- New
        print("4. View Analytics Dashboard (Pandas/NumPy)") # <-- New
        print("5. Update Customer Usage (Update) - [TODO]")
        print("6. Delete Customer (Delete) - [TODO]")
        print("7. Return to Main Menu")
        print("-------------------------------")
        
        choice = input("Enter your choice (1-7): ")
        
        if choice == '1':
            clear_screen()
            admin_add_customer()
        elif choice == '2':
            clear_screen()
            admin_view_all_customers()
        elif choice == '3':
            clear_screen()
            admin_bulk_load()
        elif choice == '4':
            clear_screen()
            admin_view_analytics()
        elif choice == '5':
            print("This feature is not yet implemented.")
            input("Press Enter to continue...")
        elif choice == '6':
            print("This feature is not yet implemented.")
            input("Press Enter to continue...")
        elif choice == '7':
            break # Exit the while loop to return to main()
        else:
            print("Invalid choice. Please try again.")
            input("Press Enter to continue...")

# --- Client Menu (from previous step, no changes) ---

def client_view_bill():
    """Client function: Allows a client to view their bill using their email."""
    clear_screen()
    print("--- View My Bill ---")
    email = input("Please enter your customer email: ")
    
    conn = sqlite3.connect('utility.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM customers WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        print("\n--- Your Customer Details ---")
        print(f"  Customer ID: {row[0]}")
        print(f"  Full Name:   {row[1]}")
        print(f"  Email:       {row[2]}")
        print("\n--- Your Bill Status ---")
        
        COST_PER_KWH = 0.12
        usage = row[3]
        amount_due = usage * COST_PER_KWH
        paid_status = "PAID" if row[4] else "NOT PAID"
        
        print(f"  Monthly Usage: {usage:.2f} kWh")
        print(f"  Amount Due:    ${amount_due:.2f} (at ${COST_PER_KWH}/kWh)")
        print(f"  Status:        {paid_status}")
    else:
        print(f"\n[Error] No customer found with the email: {email}")
        
    input("\nPress Enter to return to the client menu...")

def client_menu():
    """Displays the client-specific menu and handles choices."""
    while True:
        clear_screen()
        print("--- Client Portal ---")
        print("Welcome, valued customer!")
        print("---------------------")
        print("1. View My Bill (Read)")
        print("2. Pay My Bill (Update) - [TODO]")
        print("3. Return to Main Menu")
        print("---------------------")
        
        choice = input("Enter your choice (1-3): ")
        
        if choice == '1':
            client_view_bill()
        elif choice == '2':
            print("This feature is not yet implemented.")
            input("Press Enter to continue...")
        elif choice == '3':
            break 
        else:
            print("Invalid choice. Please try again.")
            input("Press Enter to continue...")

# --- Main Function (no changes) ---

def main():
    """Main function to run the portal application."""
    setup_database() 
    
    while True:
        clear_screen()
        print("========================================")
        print("  Welcome to the Utility Management Portal  ")
        print("========================================")
        print("1. Admin Portal")
        print("2. Client Portal")
        print("3. Exit")
        print("----------------------------------------")
        
        choice = input("Enter your choice (1-3): ")
        
        if choice == '1':
            admin_menu()
        elif choice == '2':
            client_menu()
        elif choice == '3':
            print("Exiting portal. Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1, 2, or 3.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()