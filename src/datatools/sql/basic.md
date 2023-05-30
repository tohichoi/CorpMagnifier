# 기본 쿼리

## 모든 회사에 대한 모든 리포트

```sql
select c.name as 'corp_name',
       m.name as 'market',
       r.year,
       r.quarter,
       rt.name,
       r.date,
       ri.account_code,
       ri.account_name,
       ri.amount
from Report as r
         inner join ReportItem as ri on ri.report = r.id
         inner join StockCode as sc on sc.corporation = r.corporation
         inner join corporation as c on c.id = r.corporation
         inner join market as m on sc.market = m.id
         inner join sector as st on c.sector = st.id
         inner join ReportType as rt on rt.id = r.report_type
where c.name = '삼성전자'
  and rt.name like '%포괄손익%연결%'
order by date;
```

## 값 변경

```sql
update ReportItem set amount = replace(amount, 'nan', NULL) where amount = 'nan';
```

```sql
select amount from ReportItem where amount is NULL
```

### 단지 결과를 보여주기만 한다

```sql
SELECT NULLIF(amount, 'nan') FROM ReportItem;
```


## 업종 분류

```sql
select s.name as '업종', c.name as '회사'
from corporation as c
         INNER join sector as s on c.sector is s.id
order by s.name;
```
