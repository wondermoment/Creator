const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');const ctx={};vm.createContext(ctx);vm.runInContext(fs.readFileSync('frontend/request-errors.js','utf8'),ctx);
const format=ctx.requestErrorMessage;
assert.equal(format({detail:[{loc:['body','question'],type:'string_too_long',ctx:{max_length:2000},input:'private'}]},422),'问题不能超过 2000 个字符');
assert.equal(format({detail:[{loc:['body','value'],type:'float_parsing'}]},422),'测量值请填写有效数字');
assert.equal(format({detail:'客户不存在'},404),'客户不存在');
assert.equal(format({detail:[{loc:['body','unknown'],type:'custom',input:'SECRET',msg:'internal exception'}]},422),'填写内容格式不正确，请检查后重试');
assert.equal(format(null,503),'服务暂时不可用，请稍后重试');
assert.equal(format({detail:[{type:'value_error',msg:'Value error, 请核对时间'}]},422),'请核对时间');
console.log('PASS: validation labels, numeric errors, server messages, private input omission, fallback, Chinese validation');
