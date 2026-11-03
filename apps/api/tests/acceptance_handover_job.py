"""Own-child Windows Job; no PID-based kill and no breakaway/privilege change."""
import ctypes as C
from ctypes import wintypes as W
import os
import time
import subprocess
import _winapi
from acceptance_handover_fence import apis

class Basic(C.Structure):
    _fields_=[('process_time',C.c_longlong),('job_time',C.c_longlong),('flags',W.DWORD),('minimum',C.c_size_t),('maximum',C.c_size_t),('active',W.DWORD),('affinity',C.c_size_t),('priority',W.DWORD),('scheduling',W.DWORD)]
class Accounting(C.Structure):
    _fields_=[(n,C.c_longlong) for n in ('user','kernel','period_user','period_kernel')]+[(n,W.DWORD) for n in ('faults','total','active','terminated')]
class IO(C.Structure):
    _fields_=[(name,C.c_ulonglong) for name in ('reads','writes','other','read_bytes','write_bytes','other_bytes')]
class Limits(C.Structure):
    _fields_=[('basic',Basic),('io',IO),('process_memory',C.c_size_t),('job_memory',C.c_size_t),('peak_process',C.c_size_t),('peak_job',C.c_size_t)]

def kernel():
    k=apis()[0]
    for name,args,result in (
        ('CreateJobObjectW',[C.c_void_p,W.LPCWSTR],W.HANDLE),
        ('SetInformationJobObject',[W.HANDLE,C.c_int,C.c_void_p,W.DWORD],W.BOOL),
        ('AssignProcessToJobObject',[W.HANDLE,W.HANDLE],W.BOOL),
        ('TerminateJobObject',[W.HANDLE,W.UINT],W.BOOL),
        ('QueryInformationJobObject',[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.c_void_p],W.BOOL),
        ('TerminateProcess',[W.HANDLE,W.UINT],W.BOOL),
        ('ResumeThread',[W.HANDLE],W.DWORD)):
        f=getattr(k,name);f.argtypes=args;f.restype=result
    return k

def check(ok,code):
    if not ok:raise RuntimeError(code)

class Child:
    def __init__(self,handle,pid):self.handle,self.pid=handle,pid
    def poll(self):
        code=_winapi.GetExitCodeProcess(self.handle)
        return None if code==259 else code
    def wait(self,timeout=20):
        check(_winapi.WaitForSingleObject(self.handle,int(timeout*1000))==0,'HANDOVER_OWN_CHILD_EXIT_UNCONFIRMED')
        return _winapi.GetExitCodeProcess(self.handle)
    def close(self):
        if self.handle is not None:_winapi.CloseHandle(self.handle);self.handle=None

class OwnedJob:
    def __init__(self):
        self.cleanup_confirmed=False;self.cleanup_error=False
        self.k=kernel();self.handle=self.k.CreateJobObjectW(None,None);self.children=[]
        check(self.handle,'HANDOVER_JOB_CREATE_FAILED')
        limit=Limits();limit.basic.flags=0x2000 # KILL_ON_JOB_CLOSE; handle is non-inheritable.
        try:check(self.k.SetInformationJobObject(self.handle,9,C.byref(limit),C.sizeof(limit)),'HANDOVER_JOB_POLICY_FAILED')
        except BaseException:self.close();raise
    def spawn(self,command,cwd,env,on_created=None):
        import msvcrt
        inputs=os.open(os.devnull,os.O_RDONLY);outputs=os.open(os.devnull,os.O_WRONLY)
        handles=[msvcrt.get_osfhandle(f) for f in (inputs,outputs)]
        try:
            for h in handles:os.set_handle_inheritable(h,True)
            si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESTDHANDLES
            si.hStdInput,si.hStdOutput,si.hStdError=handles[0],handles[1],handles[1]
            si.lpAttributeList={'handle_list':handles}
            ph,th,pid,_=_winapi.CreateProcess(None,subprocess.list2cmdline(list(map(str,command))),None,None,True,0x4|0x08000000,env,str(cwd),si)
        finally:
            os.close(inputs);os.close(outputs)
        child=Child(ph,pid);self.children.append(child)
        try:
            check(self.k.AssignProcessToJobObject(self.handle,ph),'HANDOVER_JOB_ASSIGN_FAILED_NO_BREAKAWAY')
            if on_created is not None:on_created(child)
            check(self.k.ResumeThread(th)!=0xffffffff,'HANDOVER_CHILD_RESUME_FAILED')
            return child
        except BaseException:
            try:
                check(self.k.TerminateProcess(ph,71),'HANDOVER_SUSPENDED_CHILD_STOP_FAILED')
                child.wait()
            except BaseException:
                self.cleanup_error=True;raise
            else:
                self.children.remove(child);child.close()
            raise
        finally:_winapi.CloseHandle(th)
    def close(self):
        if self.handle is None:
            check(self.cleanup_confirmed and not self.cleanup_error,'HANDOVER_JOB_CLEANUP_UNCONFIRMED')
            return
        handle,self.handle=self.handle,None
        try:
            check(self.k.TerminateJobObject(handle,0),'HANDOVER_JOB_STOP_UNCONFIRMED')
            for child in self.children:child.wait()
            until=time.monotonic()+15
            while True:
                count=Accounting()
                check(self.k.QueryInformationJobObject(handle,1,C.byref(count),C.sizeof(count),None),'HANDOVER_JOB_ACCOUNTING_UNAVAILABLE')
                if count.active==0:break
                check(time.monotonic()<until,'HANDOVER_JOB_DESCENDANTS_STILL_ACTIVE');time.sleep(.05)
            check(not self.cleanup_error,'HANDOVER_JOB_PRIOR_CLEANUP_UNCONFIRMED')
            self.cleanup_confirmed=True
        except BaseException:
            self.cleanup_error=True;raise
        finally:
            self.k.CloseHandle(handle)
            for child in self.children:child.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()