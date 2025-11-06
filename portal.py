import sqlite3
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import bcrypt # For password hashing
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

# --- Initialize Rich Console ---
console = Console()
CONFIG = {
    'DATABASE_FILE': 'utility.db',
    'COST_PER_KWH': 0.12,
    'EXPORT_FILENAME': 'customer_export.csv',
    'REPORT_FILENAME': 'usage_report.png',
    'SAMPLE_CSV': 'sample_customers.csv'
}
def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

# --- Password Hashing Functions ---

def hash_password(password: str) -> bytes:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def check_password(password: str, hashed: bytes) -> bool:
    """Checks if a password matches its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# --- Database Setup (NOW WITH THE FIX) ---

def setup_database():
    """
    Connects to the DB and creates BOTH tables if they don't exist.
    """
    conn = sqlite3.connect(CONFIG['DATABASE_FILE'])
    cursor = conn.cursor()
    
    # 1. Create the 'users' table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'client'
    )
    ''')
    
    # 2. MODIFIED 'customers' table with a new 'user_id' column
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        monthly_usage_kwh REAL DEFAULT 0.0,
        bill_paid BOOLEAN DEFAULT 0,
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # --- !!! THIS IS THE FIX !!! ---
    # Try to create a default admin user
    try:
        admin_hash = hash_password('admin') # Default password is 'admin'
        cursor.execute(
            "INSERT INTO users (email, password_hash, role) VALUES ('admin@portal.com', ?, 'admin')",
            (admin_hash,)
        )
        conn.commit()
        console.print("[bold yellow on black]Default admin user 'admin@portal.com' (pass: 'admin') created.[/bold yellow on black]")
    except sqlite3.IntegrityError:
        pass # Admin already exists, do nothing
    # --- END OF FIX ---
    
    conn.close()

# --- User Authentication Functions ---

def register_user():
    """Registers a new CLIENT user and creates their customer profile."""
    console.print(Panel("[bold green]Register New Client Account[/bold green]", padding=1))
    try:
        email = Prompt.ask("Enter your email")
        full_name = Prompt.ask("Enter your full name")
        password = Prompt.ask("Enter a new password", password=True)
        password_confirm = Prompt.ask("Confirm your password", password=True)

        if password != password_confirm:
            console.print("\n[bold red]Passwords do not match.[/bold red]")
            Prompt.ask("\nPress Enter to return...")
            return

        password_hash = hash_password(password)
        
        conn = sqlite3.connect('utility.db')
        cursor = conn.cursor()
        
        # 1. Create the user
        cursor.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (?, ?, 'client')",
            (email, password_hash)
        )
        new_user_id = cursor.lastrowid
        
        # 2. Create the linked customer profile
        cursor.execute(
            "INSERT INTO customers (full_name, email, user_id) VALUES (?, ?, ?)",
            (full_name, email, new_user_id)
        )
        
        conn.commit()
        conn.close()
        
        console.print(f"\n[bold green][Success] Client account for '{full_name}' created. You can now log in.[/bold green]")
        
    except sqlite3.IntegrityError:
        console.print(f"\n[bold red][Error] Email '{email}' already exists.[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]An error occurred: {e}[/bold red]")
        
    Prompt.ask("\nPress Enter to return...")


def login_user() -> tuple | None:
    """
    Logs in a user.
    Returns the user's (id, email, role) as a tuple on success, or None on failure.
    """
    console.print(Panel("[bold green]Portal Login[/bold green]", padding=1))
    email = Prompt.ask("Enter your email")
    password = Prompt.ask("Enter your password", password=True)

    conn = sqlite3.connect('utility.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, email, password_hash, role FROM users WHERE email = ?", (email,))
    user_row = cursor.fetchone()
    conn.close()
    
    if user_row:
        user_id, user_email, stored_hash, user_role = user_row
        
        if check_password(password, stored_hash):
            console.print(f"\n[bold green]Welcome, {user_email}![/bold green]")
            Prompt.ask("Press Enter to continue...")
            return (user_id, user_email, user_role) # Success!
        
    console.print("\n[bold red][Error] Invalid email or password.[/bold red]")
    Prompt.ask("\nPress Enter to return...")
    return None # Failure

# --- Admin Functions ---

def admin_create_admin_user():
    """Admin function: Creates a new ADMIN user."""
    console.print(Panel("[bold yellow]Create New Admin User[/bold yellow]", padding=1))
    try:
        email = Prompt.ask("Enter new admin's email")
        password = Prompt.ask("Enter a temporary password", password=True)
        password_hash = hash_password(password)
        
        conn = sqlite3.connect('utility.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (?, ?, 'admin')",
            (email, password_hash)
        )
        conn.commit()
        conn.close()
        
        console.print(f"\n[bold green][Success] Admin user '{email}' created.[/bold green]")
    except sqlite3.IntegrityError:
        console.print(f"\n[bold red][Error] Email '{email}' already exists.[/bold red]")
    
    Prompt.ask("\nPress Enter to return...")

def admin_add_customer():
    """Admin function: Adds a new customer (NOT a user)."""
    console.print(Panel("[bold cyan]Add New Customer (Manual Entry)[/bold cyan]", padding=1))
    console.print("[yellow]Note: This creates a customer profile without a login.\nUse 'Register' to create a client with a login.[/yellow]")
    try:
        name = Prompt.ask("Enter full name")
        email = Prompt.ask("Enter email")
        usage = float(Prompt.ask("Enter initial monthly usage (kWh)"))
        
        conn = sqlite3.connect('utility.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO customers (full_name, email, monthly_usage_kwh) VALUES (?, ?, ?)",
            (name, email, usage)
        )
        conn.commit()
        conn.close()
        
        console.print(f"\n[bold green][Success] Customer '{name}' added.[/bold green]")
    except sqlite3.IntegrityError:
        console.print(f"\n[bold red][Error] Email '{email}' already exists.[/bold red]")
    except ValueError:
        console.print("\n[bold red][Error] Invalid usage. Please enter a number.[/bold red]")
    
    Prompt.ask("\nPress Enter to return...")

def admin_view_all_customers():
    """Admin function: Displays all customer records."""
    console.print(Panel("[bold cyan]View All Customers[/bold cyan]", padding=1))
    conn = sqlite3.connect('utility.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM customers ORDER BY full_name")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        console.print("No customers found in the database.")
    else:
        table = Table(title="Customer Database")
        table.add_column("ID", style="dim", width=5)
        table.add_column("Name", style="magenta")
        table.add_column("Email", style="cyan")
        table.add_column("Usage (kWh)", style="yellow", justify="right")
        table.add_column("Bill Paid", style="green", justify="center")
        table.add_column("User ID", style="dim", justify="center") # New column
        
        for row in rows:
            paid_status = "✅ Yes" if row[4] else "❌ No"
            user_id_str = str(row[5]) if row[5] is not None else "[grey]N/A[/grey]"
            table.add_row(
                str(row[0]), row[1], row[2], f"{row[3]:.2f}", paid_status, user_id_str
            )
        console.print(table)
    Prompt.ask("\nPress Enter to return...")

def admin_update_usage():
    """Admin function: Updates a customer's usage."""
    console.print(Panel("[bold cyan]Update Customer Usage[/bold cyan]", padding=1))
    try:
        customer_id = int(Prompt.ask("Enter the Customer ID to update"))
        new_usage = float(Prompt.ask(f"Enter the new usage for Customer {customer_id}"))
        
        conn = sqlite3.connect('utility.db')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE customers SET monthly_usage_kwh = ? WHERE id = ?",
            (new_usage, customer_id)
        )
        if cursor.rowcount == 0:
            console.print(f"\n[bold red][Error] No customer found with ID {customer_id}.[/bold red]")
        else:
            conn.commit()
            console.print(f"\n[bold green][Success] Customer {customer_id}'s usage updated.[/bold green]")
        conn.close()
    except ValueError:
        console.print("\n[bold red][Error] Invalid ID or usage. Please enter numbers.[/bold red]")
    Prompt.ask("\nPress Enter to return...")

def admin_delete_customer():
    """Admin function: Deletes a customer and their linked user (if one exists)."""
    console.print(Panel("[bold red]Delete Customer[/bold red]", padding=1))
    try:
        customer_id = int(Prompt.ask("Enter the Customer ID to [bold red]DELETE[/bold red]"))
        
        if Confirm.ask(f"Are you sure you want to permanently delete Customer {customer_id}?", default=False):
            conn = sqlite3.connect('utility.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT user_id FROM customers WHERE id = ?", (customer_id,))
            result = cursor.fetchone()
            
            if not result:
                console.print(f"\n[bold red][Error] No customer found with ID {customer_id}.[/bold red]")
                conn.close()
                Prompt.ask("\nPress Enter to return...")
                return

            user_id_to_delete = result[0]
            
            cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
            
            if user_id_to_delete:
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id_to_delete,))
                console.print(f"[yellow]Linked user (ID: {user_id_to_delete}) was also deleted.[/yellow]")

            conn.commit()
            console.print(f"\n[bold green][Success] Customer {customer_id} has been deleted.[/bold green]")
            conn.close()
        else:
            console.print("\nDelete operation cancelled.")
            
    except ValueError:
        console.print("\n[bold red][Error] Invalid ID. Please enter a number.[/bold red]")
    Prompt.ask("\nPress Enter to return...")

def admin_bulk_load():
    """Admin function: Loads new customers from a CSV file using pandas."""
    console.print(Panel("[bold cyan]Bulk Load Customers from CSV[/bold cyan]", padding=1))
    
    filename = Prompt.ask("Enter the CSV filename", default="sample_customers.csv")
    
    try:
        df = pd.read_csv(filename)
        if not {'full_name', 'email', 'monthly_usage_kwh'}.issubset(df.columns):
            console.print("[bold red][Error] CSV must contain 'full_name', 'email', and 'monthly_usage_kwh' columns.[/bold red]")
            Prompt.ask("\nPress Enter to return...")
            return

        conn = sqlite3.connect('utility.db')
        # Note: These customers will not have user_id's and cannot log in
        df.to_sql('customers', conn, if_exists='append', index=False)
        conn.close()
        console.print(f"\n[bold green][Success] Added {len(df)} new customers from {filename}.[/bold green]")
        
    except FileNotFoundError:
        console.print(f"\n[bold red][Error] File not found: {filename}[/bold red]")
    except pd.errors.EmptyDataError:
        console.print(f"\n[bold red][Error] File {filename} is empty.[/bold red]")
    except sqlite3.IntegrityError as e:
        console.print(f"\n[bold red][Error] Database error. One or more emails might already exist.[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red][Error] An unexpected error occurred: {e}[/bold red]")

    Prompt.ask("\nPress Enter to return...")

def admin_export_to_csv():
    """Admin function: Exports all customer data to a CSV file."""
    console.print(Panel("[bold cyan]Export All Data to CSV[/bold cyan]", padding=1))
    
    conn = sqlite3.connect('utility.db')
    df = pd.read_sql_query("SELECT * FROM customers", conn)
    conn.close()
    
    if df.empty:
        console.print("[bold yellow]No data to export.[/bold yellow]")
    else:
        export_filename = "customer_export.csv"
        df.to_csv(export_filename, index=False)
        console.print(f"\n[bold green][Success] All {len(df)} records exported to {export_filename}[/bold green]")
        
    Prompt.ask("\nPress Enter to return...")
    
def admin_generate_report():
    """Admin function: Generates a visual report of usage."""
    console.print(Panel("[bold cyan]Generate Visual Report[/bold cyan]", padding=1))
    
    conn = sqlite3.connect('utility.db')
    df = pd.read_sql_query("SELECT full_name, monthly_usage_kwh FROM customers ORDER BY monthly_usage_kwh DESC LIMIT 10", conn)
    conn.close()
    
    if df.empty:
        console.print("[bold yellow]No data to generate report.[/bold yellow]")
    else:
        report_filename = CONFIG['REPORT_FILENAME']
        
        plt.figure(figsize=(10, 7))
        plt.bar(df['full_name'], df['monthly_usage_kwh'])
        plt.title('Top 10 Consumers by Monthly Usage')
        plt.xlabel('Customer Name')
        plt.ylabel('Usage (kWh)')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout() # Adjust plot to prevent labels from overlapping
        
        plt.savefig(report_filename)
        console.print(f"\n[bold green][Success] Report saved to {report_filename}[/bold green]")
        
    Prompt.ask("\nPress Enter to return...")

def admin_view_analytics():
    """Admin function: Views consumption and billing analytics."""
    console.print(Panel("[bold cyan]Portal Analytics Dashboard[/bold cyan]", padding=1))
    
    conn = sqlite3.connect('utility.db')
    try:
        df = pd.read_sql_query("SELECT * FROM customers", conn)
    except pd.errors.DatabaseError:
        console.print("\n[bold red]Could not read database. Is it empty?[/bold red]")
        conn.close()
        Prompt.ask("\nPress Enter to return...")
        return
    conn.close()

    if df.empty:
        console.print("\nNo customer data to analyze.")
        Prompt.ask("\nPress Enter to return...")
        return

    # ... (analytics calculations - same as before) ...
    total_customers = len(df)
    avg_usage = df['monthly_usage_kwh'].mean()
    max_usage = df['monthly_usage_kwh'].max()
    max_user = "N/A"
    if not df[df['monthly_usage_kwh'] == max_usage].empty:
        max_user = df[df['monthly_usage_kwh'] == max_usage]['full_name'].values[0]

    COST_PER_KWH = 0.12
    df['amount_due'] = df['monthly_usage_kwh'] * COST_PER_KWH
    total_revenue = df['amount_due'].sum()
    unpaid_bills_df = df[df['bill_paid'] == 0]
    total_unpaid = unpaid_bills_df['amount_due'].sum()
    
    amount_due_array = df['amount_due'].values 
    hypothetical_revenue = np.sum(amount_due_array * 1.05)
    
    # Display the report
    console.print("\n--- Customer & Usage Stats ---")
    console.print(f"  Total Customers:   {total_customers}")
    console.print(f"  Average Usage:     [yellow]{avg_usage:.2f} kWh[/yellow]")
    console.print(f"  Highest Consumer:  [magenta]{max_user}[/magenta] at [yellow]{max_usage:.2f} kWh[/yellow]")
    console.print("\n--- Billing Stats ---")
    console.print(f"  Total Billed:      [green]${total_revenue:.2f}[/green]")
    console.print(f"  Total Unpaid:      [red]${total_unpaid:.2f}[/red] ({len(unpaid_bills_df)} customers)")
    console.print("\n--- Projections (using NumPy) ---")
    console.print(f"  Total revenue with 5% price hike: [green]${hypothetical_revenue:.2f}[/green]")
    
    Prompt.ask("\nPress Enter to return...")

def admin_menu():
    """Displays the admin-specific menu."""
    
    # --- NEW: Menu Dispatch Table ---
    # We map the string '1' to the function admin_add_customer
    # Note: We don't CALL the function here (no parentheses)
    menu_options = {
        '1': admin_add_customer,
        '2': admin_view_all_customers,
        '3': admin_update_usage,
        '4': admin_delete_customer,
        '5': admin_bulk_load,
        '6': admin_view_analytics,
        '7': admin_export_to_csv,
        '8': admin_generate_report,
        '9': admin_create_admin_user,
    }

    while True:
        clear_screen()
        console.print(Panel("[bold cyan]Admin Management Portal[/bold cyan]", title="Admin Menu", padding=1))
        
        menu_text = (
            "1. Add New Customer (Manual)\n"
            "2. View All Customers\n"
            "3. Update Customer Usage\n"
            "4. Delete Customer\n"
            "5. Bulk Load Customers (CSV)\n"
            "6. View Analytics Dashboard\n"
            "7. Export All Data to CSV\n"
            "8. Generate Visual Usage Report\n"
            "9. Create New ADMIN User\n"
            "10. Logout"
        )
        console.print(menu_text)
        
        choice = Prompt.ask("\nEnter your choice (1-10)", choices=[str(i) for i in range(1, 11)])
        
        # --- REFACTORED LOGIC ---
        if choice in menu_options:
            clear_screen()
            # Look up the function in the dictionary and THEN call it
            menu_options[choice]() 
        elif choice == '10':
            break # Exit loop to log out
# --- Client Functions (MODIFIED) ---

def client_view_bill(logged_in_user_id: int):
    """Client function: Views the bill for the LOGGED IN user."""
    console.print(Panel("[bold green]View My Bill[/bold green]", padding=1))
    
    conn = sqlite3.connect(CONFIG['DATABASE_FILE']) # Using CONFIG dict
    conn.row_factory = sqlite3.Row  # <-- ADD THIS LINE
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE user_id = ?", (logged_in_user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        console.print("\n--- Your Customer Details ---")
        console.print(f"  Customer ID: {row[0]}")
        console.print(f"  Full Name:   [magenta]{row[1]}[/magenta]")
        console.print(f"  Email:       [cyan]{row[2]}[/cyan]")
        console.print("\n--- Your Bill Status ---")
        
        COST_PER_KWH = CONFIG['COST_PER_KWH'] # Using CONFIG dict
        usage = row['monthly_usage_kwh'] # <-- Access by name!
        amount_due = usage * COST_PER_KWH
        paid_status = "[bold green]✅ PAID[/bold green]" if row['bill_paid'] else "[bold red]❌ NOT PAID[/bold red]" # <-- Access by name!

        console.print(f"  Monthly Usage: [yellow]{usage:.2f} kWh[/yellow]")
        console.print(f"  Amount Due:    [bold yellow]${amount_due:.2f}[/bold yellow] (at ${COST_PER_KWH}/kWh)")
        console.print(f"  Status:        {paid_status}")
    else:
        console.print(f"\n[bold red][Error] Could not find a customer profile linked to your user account.[/bold red]")
        
    Prompt.ask("\nPress Enter to return...")

def client_pay_bill(logged_in_user_id: int):
    """Client function: Allows the LOGGED IN user to pay their bill."""
    console.print(Panel("[bold green]Pay My Bill[/bold green]", padding=1))
    
    conn = sqlite3.connect('utility.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE user_id = ?", (logged_in_user_id,))
    row = cursor.fetchone()
    
    if not row:
        console.print(f"\n[bold red][Error] Could not find a customer profile linked to your user account.[/bold red]")
        conn.close()
    elif row[4]: # if bill_paid is already 1 (True)
        console.print("\n[bold green]Your bill is already marked as PAID.[/bold green]")
        conn.close()
    else:
        COST_PER_KWH = 0.12
        amount_due = row[3] * COST_PER_KWH
        console.print(f"Your amount due is [bold yellow]${amount_due:.2f}[/bold yellow].")
        
        if Confirm.ask("Do you want to confirm this payment?"):
            cursor.execute("UPDATE customers SET bill_paid = 1 WHERE user_id = ?", (logged_in_user_id,))
            conn.commit()
            console.print("\n[bold green][Success] Thank you! Your bill is now marked as PAID.[/bold green]")
        else:
            console.print("\nPayment cancelled.")
        conn.close()
        
    Prompt.ask("\nPress Enter to return...")

def client_menu(logged_in_user_id: int):
    """Displays the client-specific menu."""
    while True:
        clear_screen()
        console.print(Panel("[bold green]Client Portal[/bold green]", title="Client Menu", padding=1))
        
        menu_text = (
            "Welcome, valued customer!\n"
            "---------------------\n"
            "1. View My Bill\n"
            "2. Pay My Bill\n"
            "3. Logout"
        )
        console.print(menu_text)
        
        choice = Prompt.ask("\nEnter your choice (1-3)", choices=['1', '2', '3'])
        
        if choice == '1':
            clear_screen(); client_view_bill(logged_in_user_id)
        elif choice == '2':
            clear_screen(); client_pay_bill(logged_in_user_id)
        elif choice == '3':
            break

# --- Post-Login Router ---

def run_portal(user_data: tuple):
    """
    Called after a successful login.
    Routes the user to the correct portal based on their role.
    """
    user_id, user_email, user_role = user_data
    
    if user_role == 'admin':
        admin_menu()
    elif user_role == 'client':
        client_menu(user_id)
    else:
        console.print(f"[bold red]Error: Unknown user role '{user_role}'.[/bold red]")
        Prompt.ask("Press Enter to log out...")

# --- Main Application ---

def main():
    """Main function to run the portal application."""
    setup_database() 
    
    while True:
        clear_screen()
        console.print(Panel(
            "[bold green]========================================\n"
            "  Welcome to the Utility Management Portal  \n"
            "========================================[/bold green]",
            title="Main Menu",
            padding=1
        ))
        
        menu_text = (
            "1. Login\n"
            "2. Register (New Clients)\n"
            "3. Exit"
        )
        console.print(menu_text)
        
        choice = Prompt.ask("\nEnter your choice (1-3)", choices=['1', '2', '3'])
        
        if choice == '1':
            clear_screen()
            user_data = login_user()
            if user_data:
                run_portal(user_data)
        elif choice == '2':
            clear_screen()
            register_user()
        elif choice == '3':
            console.print("Exiting portal. Goodbye!")
            break

if __name__ == "__main__":
    main()

