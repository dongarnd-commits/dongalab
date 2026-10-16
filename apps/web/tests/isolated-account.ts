export function isolatedAccount(){
 const username=process.env.DATCO_E2E_USER,password=process.env.DATCO_E2E_PASSWORD;
 if(process.env.DATCO_TEST_NONCE===undefined||!username||!password)throw new Error("ISOLATION_REQUIRED: use tests/isolated_run.py");
 return {username,password};
}
