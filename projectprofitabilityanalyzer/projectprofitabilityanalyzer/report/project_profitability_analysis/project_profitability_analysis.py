import frappe

def execute(filters=None):
    if filters is None:
        filters = {}
        
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Item", "fieldname": "item", "fieldtype": "Data", "width": 300},
        {"label": "Voucher Type", "fieldname": "voucher_type", "fieldtype": "Data", "width": 200, "align":"center"},
        {"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Data", "width": 200, "align":"center"},
        {"label": "Qty", "fieldname": "qty", "fieldtype": "Data", "width": 100, "align":"center"},
        {"label": "Rate", "fieldname": "rate", "fieldtype": "Currency", "width": 200},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 200}
    ]

def get_data(filters):
    if 'project' not in filters:
        return []
    
    company = frappe.db.get_value("Project", filters['project'], "company")
    currency = frappe.db.get_value("Company", company, "default_currency")


    sales_orders = frappe.db.sql("""
        SELECT
            so.name as item,
            'Sales Order' as voucher_type,
            so.name as voucher_no,
            so.total_qty as qty,
            so.net_total as rate,
            so.total as amount,
            %s as currency,
            1 as indent  
        FROM
            `tabSales Order` AS so
        WHERE
            so.project = %s AND so.docstatus = 1
    """, (currency, filters['project']), as_dict=1)

    sales_invoices = frappe.db.sql("""
        SELECT
            si.name as item,
            'Sales Invoice' as voucher_type,
            si.name as voucher_no,
            '' as qty,
            '' as rate,
            si.total as amount,
            %s as currency,
            1 as indent 
        FROM
            `tabSales Invoice` AS si
        WHERE
            si.project = %s AND si.docstatus = 1
    """, (currency, filters['project']), as_dict=1)

    purchase_invoices = frappe.db.sql("""
        SELECT
            pii.description as item,
            # pi.name as item,
            'Purchase Invoice' as voucher_type,
            pi.name as voucher_no,
            pii.qty as qty,
            pii.rate as rate,
            pii.amount as amount,
            %s as currency,
            1 as indent 
        FROM
            `tabPurchase Invoice` AS pi
        INNER JOIN
            `tabPurchase Invoice Item` AS pii ON pi.name = pii.parent
        INNER JOIN
            `tabItem` AS i ON pii.item_code = i.name
        WHERE
            pii.project = %s
            AND pi.docstatus = 1
            AND i.is_stock_item = 0
    """, (currency, filters['project']), as_dict=1)


    stock_entries = frappe.db.sql("""
        SELECT
            sed.item_code as item,
            'Stock Entry' as voucher_type,
            se.name as voucher_no,
            IFNULL(SUM(sed.qty), 0) as qty,
            sed.basic_rate as rate,
            sed.amount as amount,
            %s as currency,
            1 as indent 
        FROM
            `tabStock Entry` AS se
        LEFT JOIN
            `tabStock Entry Detail` AS sed ON se.name = sed.parent
        WHERE
            sed.project = %s AND se.purpose = 'Material Issue' AND se.docstatus = 1
        GROUP BY
            sed.item_code
    """, (currency, filters['project']), as_dict=1)

    timesheets = frappe.db.sql("""
        SELECT
            tsd.activity_type as item,
            'Timesheet' as voucher_type,
            ts.name as voucher_no,
            tsd.hours as qty,
            # IFNULL(ts.total_costing_amount / NULLIF(ts.total_hours, 0), 0) as rate,
            tsd.costing_rate as rate,
            # tsd.hours * IFNULL(ts.total_costing_amount / NULLIF(ts.total_hours, 0), 0) as amount,
            tsd.hours * tsd.costing_rate as amount,
            %s as currency,
            1 as indent 
        FROM
            `tabTimesheet` AS ts
        LEFT JOIN
            `tabTimesheet Detail` AS tsd ON ts.name = tsd.parent
        WHERE
            tsd.project = %s AND ts.docstatus = 1
    """, (currency, filters['project']), as_dict=1)

    # expense_claims = frappe.db.sql("""
    #     SELECT
    #         'Expense Claim' as voucher_type,
    #         ec.name as voucher_no,
    #         '' as qty,
    #         '' as rate,
    #         ec.total_sanctioned_amount as amount,
    #         ec.employee_name as item,
    #         %s as currency,
    #         1 as indent 
    #     FROM
    #         `tabExpense Claim` AS ec
    #     WHERE
    #         ec.project = %s AND ec.docstatus = 1
    # """, (currency, filters['project']), as_dict=1)

    expense_claims = frappe.db.sql("""
        SELECT
            ecd.expense_type as item,
            'Expense Claim' as voucher_type,
            ec.name as voucher_no,
            '1' as qty,
            ecd.amount as rate,
            # ec.total_sanctioned_amount as amount,
            ecd.amount as amount,
            # ec.employee_name as item,
            %s as currency,
            1 as indent 
        FROM
            `tabExpense Claim` AS ec
        LEFT JOIN
            `tabExpense Claim Detail` AS ecd ON ec.name = ecd.parent
        WHERE
            ecd.project = %s AND ec.docstatus = 1
    """, (currency, filters['project']), as_dict=1)

    total_amount_orders = sum(so['amount'] for so in sales_orders)
    total_amount_invoices = sum(si['amount'] for si in sales_invoices)
    total_amount_purchases = sum(pi['amount'] for pi in purchase_invoices)
    total_amount_stock_entries = sum(se['amount'] for se in stock_entries)
    total_amount_timesheets = sum(ts['amount'] for ts in timesheets)
    total_amount_expense_claims = sum(ec['amount'] for ec in expense_claims)
    total_cost = sum([total_amount_expense_claims, total_amount_timesheets, total_amount_stock_entries, total_amount_purchases])
    margin = total_amount_invoices - total_cost
    margin_ord = total_amount_orders - total_cost

    if total_amount_invoices != 0:
        margin_per = (margin / total_amount_invoices) * 100
    else:
        margin_per = " "

    if total_amount_orders != 0:
        margin_per_ord = (margin / total_amount_orders ) * 100
    else:
        margin_per_ord = " "

    data = []
    if total_amount_orders:
        data += [
            {
                'item': 'Total Sales Order Amount',
                'voucher_type': '',
                'voucher_no': '',
                'qty': '',
                'rate': '',
                'amount': total_amount_orders,
                'currency': currency,
                'indent': 0  
            }
        ] + sales_orders

    if total_amount_invoices:
        data += [
            {
                'item': 'Total Billed Amount',
                'voucher_type': '',
                'voucher_no': '',
                'qty': '',
                'rate': '',
                'amount': total_amount_invoices,
                'currency': currency,
                'indent': 0  
            }
        ] + sales_invoices

    if total_amount_purchases:
        data += [
            {
                'item': 'Total Purchase Cost',
                'voucher_type': '',
                'voucher_no': '',
                'qty': '',
                'rate': '',
                'amount': total_amount_purchases,
                'currency': currency,
                'indent': 0  
            }
        ] + purchase_invoices

    if total_amount_stock_entries:
        data += [
            {
                'item': 'Total Consumed Material Cost',
                'voucher_type': '',
                'voucher_no': '',
                'qty': '',
                'rate': '',
                'amount': total_amount_stock_entries,
                'currency': currency,
                'indent': 0  
            }
        ] + stock_entries

    if total_amount_timesheets:
        data += [
            {
                'item': 'Total Timesheet Cost',
                'voucher_type': '',
                'voucher_no': '',
                'qty': '',
                'rate': '',
                'amount': total_amount_timesheets,
                'currency': currency,
                'indent': 0 
            }
        ] + timesheets

    if total_amount_expense_claims:
        data += [
            {
                'item': 'Total Expense Claim Cost',
                'voucher_type': '',
                'voucher_no': '',
                'qty': '',
                'rate': '',
                'amount': total_amount_expense_claims,
                'currency': currency,
                'indent': 0 
            }
        ] + expense_claims


    data += [
        {
            'item': 'Total Cost',
            'voucher_type': '',
            'voucher_no': '',
            'qty': '',
            'rate': '',
            'amount': total_cost,
            'currency': currency,
            'indent': 0 
        }
    ] + [
        {
            'item': 'Margin (Based on billing)',
            'voucher_type': '',
            'voucher_no': '',
            'qty': '',
            'rate': '',
            'amount': margin,
            'currency': currency,
            'indent': 0 
        }
    ] + [
        {
            'item': 'Margin % (Based on billing)',
            'voucher_type': '',
            'voucher_no': '',
            'qty': '',
            'rate': '',
            'amount': margin_per,
            'currency': currency,
            'is_percentage': True,
            'indent': 0 
        }
    ] + [
        {
            'item': 'Margin (Against order amount)',
            'voucher_type': '',
            'voucher_no': '',
            'qty': '',
            'rate': '',
            'amount': margin_ord,
            'currency': currency,
            'indent': 0 
        }
    ] + [
        {
            'item': 'Margin % (Against order amount)',
            'voucher_type': '',
            'voucher_no': '',
            'qty': '',
            'rate': '',
            'amount': margin_per_ord,
            'currency': currency,
            'is_percentage': True,
            'indent': 0 
        }
    ]

    return data


