from test_journey import borrower,otp,create
from app.schemas.journey import BankAccount
from pydantic import ValidationError
import pytest

def test_bank_validation():
    with pytest.raises(ValidationError):BankAccount(bank_name='SBI',account_holder='Aarav',account_last4='123456789',branch='Chennai',ifsc='INVALID')

def test_bank_accounts_persist_and_officer_review(client,auth):
    h,p=borrower(client,91);proof,_=otp(client,p['mobile'],'kyc',h)
    account={'bank_name':'State Bank of India','account_holder':p['business'],'account_last4':'4821','account_type':'Current','branch':'Chennai','ifsc':'SBIN0001234'}
    r=client.post('/api/borrower/applications',headers=h,json={'kyc_proof':proof['kyc_proof'],'pan':p['pan'],'dob':p['dob'],'purpose':'Equipment purchase','requested_amount':1000000,'tenure_months':36,'consents':['kyc','bank','tax','bureau','processing'],'bank_accounts':[account]})
    assert r.status_code==201,r.text
    a=r.json();id=a['id'];assert a['data']['bank_accounts'][0]['ownership_status']=='Pending review'
    r=client.post(f'/api/borrower/applications/{id}/fetch',headers=h,json={});assert r.status_code==201
    a=client.get(f'/api/applications/{id}',headers=auth).json();doc=next(d for d in a['documents'] if d['kind']=='bank')
    body={'revision':a['revision'],'items':[{'account_index':0,'document_id':doc['id'],'ownership_verified':True,'notes':'Holder and account reference checked'}]}
    assert client.post(f'/api/applications/{id}/bank-review',headers=h,json=body).status_code==401
    bad={**body,'items':[{**body['items'][0],'document_id':'not-owned'}]}
    assert client.post(f'/api/applications/{id}/bank-review',headers=auth,json=bad).status_code==422
    assert client.post(f'/api/applications/{id}/bank-review',headers=auth,json=body).status_code==201
    current=client.get(f'/api/applications/{id}',headers=auth).json()
    assert current['revision']==a['revision']+1
    assert current['data']['bank_accounts'][0]['statement_reference']==doc['id']
    assert current['data']['bank_accounts'][0]['ownership_status']=='Reviewed by officer'
    assert client.post(f'/api/applications/{id}/bank-review',headers=auth,json=body).status_code==409
