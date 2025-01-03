// Copyright (c) 2024, Craft and contributors
// For license information, please see license.txt
/* eslint-disable */
frappe.query_reports["Project Profitability Analysis"] = {
    "filters": [
        {
            'fieldname': 'project',
            'label': __("Project"),
            'fieldtype': 'Link',
            'options': 'Project',
            'reqd':1
        }
    ],
    "formatter": function (value, row, column, data, default_formatter) {
        if (column.fieldname === "voucher_no") {
            value = frappe.format(value, {fieldtype: 'Link', options: data.voucher_type});
        } else if (column.fieldname === "qty") {
            if (value === '') {
                value = '';
            } else {
                value = parseFloat(value).toFixed(2);
            }
        } else if (column.fieldname === "rate") {
            if (value === '' || value === 0) {
                value = '';      
            } else {
                value = parseFloat(value).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + " " + data.currency;
            }
        } else if (column.fieldname === "amount") {
            if (value === ' ' || value === '' || value === 0) {
                value = '';
            } else if (data.is_percentage) {
                value = parseFloat(value).toFixed(2) + "%";
            } else {
                value = parseFloat(value).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + " " + data.currency;
            }
        } else {
            value = default_formatter(value, row, column, data);
        }
        if (data && data.indent == 0) {
            value = $(`<span>${value}</span>`);
            var $value = $(value).css("font-weight", "bold");
            value = $value.wrap("<p></p>").parent().html();
        }
        return value;
    }
};