select c.name, m.name, r.year, r.quarter, rt.name, r.date, ri.account_code, ri.account_name, ri.amount
from report as r
inner join ReportItem as ri on ri.report = r.id
inner join StockCode as sc on sc.corporation = r.corporation
inner join corporation as c on c.id = r.corporation
inner join market as m on sc.market = m.id
inner join sector as st on c.sector = st.id
inner join ReportType as rt on rt.id = r.report_type
where c.name = "삼성전자"