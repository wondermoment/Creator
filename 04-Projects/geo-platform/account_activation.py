"""One-use local customer onboarding. Never changes an existing account password."""
import hashlib
from datetime import datetime,timedelta,timezone
from fastapi import Request,Response,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field

class Activate(BaseModel):
    token:str=Field(min_length=32,max_length=180)
    password:str=Field(min_length=10,max_length=128)

def register(g):
    with g['db']() as c:
        c.execute('CREATE TABLE IF NOT EXISTS account_invites(token_hash TEXT PRIMARY KEY,identity TEXT NOT NULL,project_id TEXT NOT NULL REFERENCES projects(id),role TEXT NOT NULL,expires TEXT NOT NULL,used TEXT)')
    def invite(c,identity,pid,role='owner'):
        identity=g['identity_value'](identity)
        if c.execute('SELECT id FROM users WHERE identity=?',(identity,)).fetchone():raise HTTPException(409,'账号已存在，请通过企业成员管理添加权限')
        if role not in ('owner','editor','reviewer','viewer'):raise HTTPException(422,'角色无效')
        token=g['secrets'].token_urlsafe(40)
        # Only the most recent unused invite for this identity and tenant remains active.
        c.execute('UPDATE account_invites SET used=? WHERE identity=? AND project_id=? AND used IS NULL',(g['now'](),identity,pid))
        c.execute('INSERT INTO account_invites VALUES(?,?,?,?,?,NULL)',(hashlib.sha256(token.encode()).hexdigest(),identity,pid,role,(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat(timespec='seconds')))
        return token
    def find(c,token):
        row=c.execute('SELECT * FROM account_invites WHERE token_hash=? AND used IS NULL AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),g['now']())).fetchone()
        if not row:raise HTTPException(404,'开通链接无效或已过期，请联系空间管理员')
        return row
    @g['app'].get('/activate')
    def page():return FileResponse(g['ROOT']/'static/activate.html')
    @g['app'].get('/api/activation')
    def info(token:str):
        with g['db']() as c:
            row=find(c,token);p=g['project'](c,row['project_id']);identity=row['identity']
            return {'identity_hint':identity[:3]+'****'+identity[-4:],'project':p['name'],'website':p['website'],'expires':row['expires']}
    @g['app'].post('/api/activation')
    def activate(body:Activate,request:Request,response:Response):
        g['limit_auth'](request)
        with g['db']() as c:
            row=find(c,body.token)
            if c.execute('SELECT id FROM users WHERE identity=?',(row['identity'],)).fetchone():raise HTTPException(409,'该账号已注册；不会覆盖密码或自动追加权限')
            user=g['uid']();c.execute('INSERT INTO users VALUES(?,?,?,?)',(user,row['identity'],g['password_hash'](body.password),g['now']()))
            c.execute('INSERT INTO members VALUES(?,?,?)',(row['project_id'],user,row['role']))
            c.execute('UPDATE account_invites SET used=? WHERE token_hash=?',(g['now'](),row['token_hash']))
            g['event'](c,row['project_id'],user,'客户开通独立账号','只加入当前企业空间')
            return {**g['login_session'](c,user,response),'project_id':row['project_id']}
    return invite
