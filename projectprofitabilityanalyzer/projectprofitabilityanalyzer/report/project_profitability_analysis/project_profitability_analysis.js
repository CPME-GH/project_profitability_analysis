frappe.query_reports["Project Profitability Analysis"] = {
    "filters": [
        {
            'fieldname': 'project',
            'label': __("Project"),
            'fieldtype': 'Link',
            'options': 'Project',
            'reqd': 1
        },
        {
            'fieldname': 'from_date',
            'label': __("From Date"),
            'fieldtype': 'Date',
            'reqd': 0
        },
        {
            'fieldname': 'to_date',
            'label': __("To Date"),
            'fieldtype': 'Date',
            'reqd': 0
        }
    ],
    "formatter": function (value, row, column, data, default_formatter) {
        try {
            if (column.fieldname === "voucher_no" && data.voucher_type) {
                value = frappe.format(value, { fieldtype: 'Link', options: data.voucher_type });
            } else if (column.fieldname === "qty") {
                value = (value === null || value === '' || value === undefined) ? '' : parseFloat(value).toFixed(2);
            } else if (column.fieldname === "rate") {
                value = (value === null || value === '' || value === 0 || value === undefined) ? '' :
                        parseFloat(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " " + (data.currency || '');
            } else if (column.fieldname === "amount") {
                if (value === null || value === '' || value === 0 || value === undefined) {
                    value = '';
                } else if (data.is_percentage) {
                    value = parseFloat(value).toFixed(2) + "%";
                } else {
                    value = parseFloat(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " " + (data.currency || '');
                }
            } else {
                value = default_formatter(value, row, column, data);
            }

            if (data && data.indent === 0) {
                value = $(`<span>${value}</span>`).css("font-weight", "bold").wrap("<p></p>").parent().html();
            }

            return value;
        } catch (e) {
            frappe.log_error(`Formatter error: ${e.message}`, "Project Profitability Analysis");
            return default_formatter(value, row, column, data);
        }
    }
};