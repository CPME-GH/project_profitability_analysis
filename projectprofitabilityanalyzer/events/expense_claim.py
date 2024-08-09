def before_submit(doc,method):
    project = doc.project

    for i in doc.expenses:
        if not i.project:
            i.project = project