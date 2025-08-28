from datetime import datetime
import frappe
from frappe.utils import getdate

def execute(filters=None):
    if filters is None:
        filters = {}
        
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Item", "fieldname": "item", "fieldtype": "Data", "width": 300},
        {"label": "Voucher Type", "fieldname": "voucher_type", "fieldtype": "Data", "width": 200, "align": "center"},
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Data", "width": 200, "align": "center"},
        {"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Data", "width": 200, "align": "center"},
        {"label": "Qty", "fieldname": "qty", "fieldtype": "Data", "width": 100, "align": "center"},
        {"label": "Rate", "fieldname": "rate", "fieldtype": "Currency", "width": 200},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 200},
    ]

def get_data(filters):
    if not filters.get('project'):
        return []
    
    from_date = datetime.strptime(filters.get('from_date'), '%Y-%m-%d').date() if filters.get('from_date') else None
    to_date = datetime.strptime(filters.get('to_date'), '%Y-%m-%d').date() if filters.get('to_date') else None
    
    condition_so = "so.project = '{0}' AND so.docstatus = 1".format(filters['project'])
    
    if filters.get('from_date') and filters.get('to_date'):
        condition_so += " AND so.transaction_date BETWEEN '{0}' AND '{1}'".format(from_date, to_date)
    
    company = frappe.db.get_value("Project", filters['project'], "company")
    if not company:
        return []
    
    currency = frappe.db.get_value("Company", company, "default_currency") or "USD"
    
    sales_orders = frappe.db.sql("""
        SELECT
            soi.item_code as item,
            'Sales Order' as voucher_type,
            so.name as voucher_no,
            soi.qty as qty,
            soi.rate as rate,
            soi.net_amount as amount,
            %s as currency,
            1 as indent
        FROM
            `tabSales Order` AS so
        INNER JOIN
            `tabSales Order Item` AS soi ON soi.parent = so.name
        INNER JOIN
            `tabItem` AS i ON soi.item_code = i.name
        WHERE
            {0}
    """.format(condition_so), currency, as_dict=1)

    condition_si = "si.project = '{0}' AND si.docstatus = 1".format(filters['project'])
    
    if filters.get('from_date') and filters.get('to_date'):
        condition_si += " AND si.posting_date BETWEEN '{0}' AND '{1}'".format(from_date, to_date)

    sales_invoices = frappe.db.sql("""
        SELECT
            sii.item_code as item,
            'Sales Invoice' as voucher_type,
            si.name as voucher_no,
            sii.qty as qty,
            sii.rate as rate,
            sii.net_amount as amount,
            %s as currency,
            1 as indent 
        FROM
            `tabSales Invoice` AS si
        INNER JOIN
            `tabSales Invoice Item` AS sii ON sii.parent = si.name
        INNER JOIN
            `tabItem` AS i ON sii.item_code = i.name
        WHERE
            {0}
    """.format(condition_si), currency, as_dict=1)

    condition_dn = "dn.project = '{0}' AND dn.docstatus = 1 AND dni.incoming_rate > 0 AND i.is_stock_item = 1".format(filters['project'])
    
    if filters.get('from_date') and filters.get('to_date'):
        condition_dn += " AND dn.posting_date BETWEEN '{0}' AND '{1}'".format(from_date, to_date)
    
    delivery_notes = frappe.db.sql("""
        SELECT
            dni.item_code as item,
            'Delivery Note' as voucher_type,
            dn.name as voucher_no,
            dni.qty as qty,
            dni.incoming_rate as rate,
            (dni.qty * dni.incoming_rate) as amount,
            %s as currency,
            1 as indent 
        FROM
            `tabDelivery Note` AS dn
        INNER JOIN
            `tabDelivery Note Item` AS dni ON dn.name = dni.parent
        INNER JOIN
            `tabItem` AS i ON dni.item_code = i.name
        WHERE
            {0}
    """.format(condition_dn), currency, as_dict=1)

    condition_pb = "dn.project = '{0}' AND dn.docstatus = 1 AND dni.item_code IN (SELECT new_item_code FROM `tabProduct Bundle`) AND dni.amount > 0".format(filters['project'])
    
    if filters.get('from_date') and filters.get('to_date'):
        condition_pb += " AND dn.posting_date BETWEEN '{0}' AND '{1}'".format(from_date, to_date)

    product_bundles = frappe.db.sql("""
        SELECT
            dni.item_code as item,
            'Delivery Note' as voucher_type,
            dn.name as voucher_no,
            dni.qty as qty,
            dni.rate as rate,
            dni.amount as amount,
            %s as currency,
            1 as indent
        FROM `tabDelivery Note` dn
        JOIN `tabDelivery Note Item` dni ON dn.name = dni.parent
        WHERE {0}
    """.format(condition_pb), currency, as_dict=1)

    condition_pi = "pii.project = '{0}' AND pi.docstatus = 1 AND i.is_stock_item = 0".format(filters['project'])
    
    if filters.get('from_date') and filters.get('to_date'):
        condition_pi += " AND pi.posting_date BETWEEN '{0}' AND '{1}'".format(from_date, to_date)

    purchase_invoices = frappe.db.sql("""
        SELECT
            pii.description as item,
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
            {0}
    """.format(condition_pi), currency, as_dict=1)

    condition_je = "jea.project = '{0}' AND je.docstatus = 1 AND jea.debit_in_account_currency > 0".format(filters['project'])
    
    if filters.get('from_date') and filters.get('to_date'):
        condition_je += " AND je.posting_date BETWEEN '{0}' AND '{1}'".format(from_date, to_date)

    journal_entries = frappe.db.sql("""
        SELECT
            jea.account as item,
            'Journal Entry' as voucher_type,
            je.name as voucher_no,
            1 as qty,
            jea.debit_in_account_currency as rate,
            jea.debit_in_account_currency as amount,
            %s as currency,
            1 as indent
        FROM
            `tabJournal Entry` AS je
        INNER JOIN
            `tabJournal Entry Account` AS jea ON je.name = jea.parent
        WHERE
            {0}
    """.format(condition_je), currency, as_dict=1)

    condition_se = "sed.project = '{0}' AND se.docstatus = 1 AND se.stock_entry_type IN ('Project Material Issue', 'Project Material Return')".format(filters['project'])
    
    if filters.get('from_date') and filters.get('to_date'):
        condition_se += " AND se.posting_date BETWEEN '{0}' AND '{1}'".format(from_date, to_date)

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
            {0}
        GROUP BY
            sed.item_code
    """.format(condition_se), currency, as_dict=1)

    condition_ec = "ec.project = '{0}' AND ec.docstatus = 1".format(filters['project'])
    
    if filters.get('from_date') and filters.get('to_date'):
        condition_ec += " AND ec.posting_date BETWEEN '{0}' AND '{1}'".format(from_date, to_date)

    expense_claims = frappe.db.sql("""
        SELECT
            ecd.expense_type as item,
            'Expense Claim' as voucher_type,
            ec.name as voucher_no,
            '1' as qty,
            ecd.amount as rate,
            ecd.amount as amount,
            %s as currency,
            1 as indent 
        FROM
            `tabExpense Claim` AS ec
        LEFT JOIN
            `tabExpense Claim Detail` AS ecd ON ec.name = ecd.parent
        WHERE
            {0}
    """.format(condition_ec), currency, as_dict=1)

    condition_da = "da.project = '{0}' AND da.docstatus = 1".format(filters['project'])
    
    if filters.get('from_date') and filters.get('to_date'):
        condition_da += " AND da.selected_date BETWEEN '{0}' AND '{1}'".format(from_date, to_date)

    total_manpower_cost = frappe.db.sql("""
        SELECT
            e.name as item,
            e.custom_hourly_rate as rate,
            SUM(da.total_man_hour) as qty,
            SUM(da.total_man_hour) * e.custom_hourly_rate as amount,
            %s as currency,
            1 as indent
        FROM 
            `tabDaily Attendance` da
        JOIN 
            `tabEmployee` e ON da.employee = e.name
        WHERE 
            {0}
        GROUP BY 
            da.project, da.employee
    """.format(condition_da), currency, as_dict=1)

    total_amount_orders = sum(so['amount'] for so in sales_orders)
    total_amount_invoices = sum(si['amount'] for si in sales_invoices)
    total_amount_bundles = sum(dnb['amount'] for dnb in product_bundles)
    total_amount_delivery_notes = total_amount_bundles + sum(dn['amount'] for dn in delivery_notes)
    total_amount_purchases = sum(pi['amount'] for pi in purchase_invoices)
    total_amount_journal_entries = sum(je['amount'] for je in journal_entries)
    total_amount_stock_entries = sum(se['amount'] for se in stock_entries)
    total_amount_expense_claims = sum(ec['amount'] for ec in expense_claims)
    total_manpower = sum(mp['amount'] for mp in total_manpower_cost)
    total_cost = sum([total_amount_expense_claims, total_amount_stock_entries, total_amount_purchases, total_amount_delivery_notes, total_manpower, total_amount_journal_entries])
    margin = total_amount_invoices - total_cost
    margin_ord = total_amount_orders - total_cost
   
    if total_amount_invoices != 0:
        margin_per = (margin / total_amount_invoices) * 100
    else:
        margin_per = 0

    if total_amount_orders != 0:
        margin_per_ord = (margin / total_amount_orders) * 100
    else:
        margin_per_ord = 0

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

    if total_amount_delivery_notes:
        data += [
            {
                'item': 'Total Delivery Note Cost',
                'voucher_type': '',
                'voucher_no': '',
                'qty': '',
                'rate': '',
                'amount': total_amount_delivery_notes,
                'currency': currency,
                'indent': 0 
            }
        ] + delivery_notes + product_bundles

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

    if total_amount_journal_entries:
        data += [
            {
                'item': 'Total Journal Entry Cost',
                'voucher_type': '',
                'voucher_no': '',
                'qty': '',
                'rate': '',
                'amount': total_amount_journal_entries,
                'currency': currency,
                'indent': 0 
            }
        ] + journal_entries

    if total_manpower_cost:
        data += [
            {
                'item': 'Total Manpower Cost',
                'voucher_type': '',
                'voucher_no': '',
                'qty': '',
                'rate': '',
                'amount': total_manpower,
                'currency': currency,
                'indent': 0 
            }
        ] + total_manpower_cost

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
            'amount': total_cost or '',
            'currency': currency,
            'indent': 0 
        },
        {
            'item': 'Margin (Based on billing)',
            'voucher_type': '',
            'voucher_no': '',
            'qty': '',
            'rate': '',
            'amount': margin or '',
            'currency': currency,
            'indent': 0 
        },
        {
            'item': 'Margin % (Based on billing)',
            'voucher_type': '',
            'voucher_no': '',
            'qty': '',
            'rate': '',
            'amount': margin_per or '',
            'currency': currency,
            'is_percentage': True,
            'indent': 0 
        },
        {
            'item': 'Margin (Against order amount)',
            'voucher_type': '',
            'voucher_no': '',
            'qty': '',
            'rate': '',
            'amount': margin_ord or '',
            'currency': currency,
            'indent': 0 
        },
        {
            'item': 'Margin % (Against order amount)',
            'voucher_type': '',
            'voucher_no': '',
            'qty': '',
            'rate': '',
            'amount': margin_per_ord or '',
            'currency': currency,
            'is_percentage': True,
            'indent': 0 
        }
    ]
    return data