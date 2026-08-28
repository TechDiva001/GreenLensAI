path = 'crud/report_crud.py'
content = open(path).read()
content = content.replace('"Submitted"', '"SUBMITTED"').replace('"Under Verification"', '"UNDER_REVIEW"').replace('"Resolved"', '"RESOLVED"').replace('"Verification Failed"', '"REJECTED"')
open(path, 'w').write(content)
