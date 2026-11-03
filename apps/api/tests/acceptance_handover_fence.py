"""Temporary Windows fences and read-only identity, never command lines/env."""
import ctypes as C
from ctypes import wintypes as W
from functools import lru_cache
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
import subprocess
import acceptance_release as release


def fail(code):
    raise RuntimeError(code)


class BasicInfo(C.Structure):
    _fields_=[('reserved1',C.c_void_p),('peb',C.c_void_p),('reserved2',C.c_void_p*2),('pid',C.c_void_p),('reserved3',C.c_void_p)]


class ProcessEntry(C.Structure):
    _fields_=[('size',W.DWORD),('usage',W.DWORD),('pid',W.DWORD),('heap',C.c_size_t),('module',W.DWORD),('threads',W.DWORD),('parent',W.DWORD),('priority',W.LONG),('flags',W.DWORD),('name',W.WCHAR*260)]


class AttributeTag(C.Structure):
    _fields_=[('attributes',W.DWORD),('tag',W.DWORD)]


@lru_cache(maxsize=1)
def apis():
    if os.name!='nt' or C.sizeof(C.c_void_p)!=8:fail('HANDOVER_WINDOWS_X64_REQUIRED')
    k=C.WinDLL('kernel32',use_last_error=True);n=C.WinDLL('ntdll')
    def bind(dll,name,args,result=W.BOOL):
        function=getattr(dll,name);function.argtypes,function.restype=args,result
    H,P,D=W.HANDLE,C.c_void_p,W.DWORD
    bind(k,'CreateFileW',[W.LPCWSTR,D,D,P,D,D,H],H)
    bind(k,'CloseHandle',[H]);bind(k,'ReadFile',[H,P,D,C.POINTER(D),P])
    bind(k,'SetFilePointerEx',[H,C.c_longlong,P,D])
    bind(k,'GetFileInformationByHandleEx',[H,C.c_int,P,D])
    bind(k,'GetFinalPathNameByHandleW',[H,W.LPWSTR,D,D],D)
    bind(k,'OpenProcess',[D,W.BOOL,D],H)
    bind(k,'GetProcessTimes',[H]+[C.POINTER(W.FILETIME)]*4)
    bind(k,'QueryFullProcessImageNameW',[H,D,W.LPWSTR,C.POINTER(D)])
    bind(k,'IsWow64Process',[H,C.POINTER(W.BOOL)])
    bind(k,'ReadProcessMemory',[H,P,P,C.c_size_t,C.POINTER(C.c_size_t)])
    bind(k,'CreateToolhelp32Snapshot',[D,D],H)
    bind(k,'Process32FirstW',[H,C.POINTER(ProcessEntry)])
    bind(k,'Process32NextW',[H,C.POINTER(ProcessEntry)])
    bind(n,'NtQueryInformationProcess',[H,D,P,D,C.POINTER(D)],W.LONG)
    return k,n


class FileFence:
    """Share 0 for entrypoint; read-only sharing for stopped legacy state."""
    def __init__(self,path,exclusive=True):
        self.path=release.no_links(path);self.handle=None;k,_=apis()
        handle=k.CreateFileW(str(release.fs_path(self.path)),0x80000000,0 if exclusive else 1,None,3,0x00200000|0x08000000,None)
        if handle in (None,C.c_void_p(-1).value):fail('HANDOVER_FENCE_ACQUIRE_FAILED')
        self.handle=handle
        try:
            tag=AttributeTag()
            if not k.GetFileInformationByHandleEx(handle,9,C.byref(tag),C.sizeof(tag)):fail('HANDOVER_FENCE_ATTRIBUTE_CHECK_FAILED')
            if tag.attributes&(0x400|0x10):fail('HANDOVER_FENCE_LINK_OR_DIRECTORY_REJECTED')
            final=C.create_unicode_buffer(32768);length=k.GetFinalPathNameByHandleW(handle,final,len(final),0)
            if not 0<length<len(final):fail('HANDOVER_FENCE_FINAL_PATH_FAILED')
            if str(release.normal_path(final.value)).casefold()!=str(self.path).casefold():fail('HANDOVER_FENCE_PATH_MISMATCH')
        except BaseException:self.close();raise
    def sha256(self):
        if self.handle is None:fail('HANDOVER_FENCE_CLOSED')
        k,_=apis()
        if not k.SetFilePointerEx(self.handle,0,None,0):fail('HANDOVER_FENCE_SEEK_FAILED')
        digest=sha256();buffer=C.create_string_buffer(65536)
        while True:
            count=W.DWORD()
            if not k.ReadFile(self.handle,buffer,len(buffer),C.byref(count),None):fail('HANDOVER_FENCE_READ_FAILED')
            if not count.value:return digest.hexdigest()
            digest.update(buffer.raw[:count.value])
    def close(self):
        if self.handle is not None:
            handle,self.handle=self.handle,None
            if not apis()[0].CloseHandle(handle):fail('HANDOVER_FENCE_CLOSE_FAILED')
    def __enter__(self):return self
    def __exit__(self,*_):self.close()


def read_memory(k,handle,address,size):
    if not address or not 0<size<=65536:fail('HANDOVER_PROCESS_MEMORY_RANGE_REJECTED')
    buffer=C.create_string_buffer(size);count=C.c_size_t()
    if not k.ReadProcessMemory(handle,address,buffer,size,C.byref(count)) or count.value!=size:fail('HANDOVER_PROCESS_CWD_READ_FAILED')
    return buffer.raw


def process_identity(pid,hash_image=False):
    if type(pid) is not int or not 0<pid<=0xffffffff:fail('HANDOVER_PID_INVALID')
    k,n=apis();handle=k.OpenProcess(0x0400|0x0010,False,pid)
    if not handle:fail('HANDOVER_PROCESS_OPEN_FAILED')
    try:
        wow=W.BOOL()
        if not k.IsWow64Process(handle,C.byref(wow)) or wow.value:fail('HANDOVER_NATIVE_PROCESS_REQUIRED')
        times=[W.FILETIME() for _ in range(4)]
        if not k.GetProcessTimes(handle,*(C.byref(t) for t in times)):fail('HANDOVER_PROCESS_TIME_FAILED')
        created=str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)
        image=C.create_unicode_buffer(32768);size=W.DWORD(32768)
        if not k.QueryFullProcessImageNameW(handle,0,image,C.byref(size)):fail('HANDOVER_PROCESS_IMAGE_FAILED')
        basic=BasicInfo()
        if n.NtQueryInformationProcess(handle,0,C.byref(basic),C.sizeof(basic),None):fail('HANDOVER_PROCESS_BASIC_INFO_FAILED')
        parameters=struct.unpack('<Q',read_memory(k,handle,basic.peb+0x20,8))[0]
        length,maximum,address=struct.unpack('<HH4xQ',read_memory(k,handle,parameters+0x38,16))
        if not 0<length<=maximum<=65534 or length%2:fail('HANDOVER_PROCESS_CWD_LENGTH_INVALID')
        cwd=release.normal_path(read_memory(k,handle,address,length).decode('utf-16-le'))
        if not cwd.is_absolute():fail('HANDOVER_PROCESS_CWD_NOT_ABSOLUTE')
        snapshot=k.CreateToolhelp32Snapshot(2,0)
        if snapshot in (None,C.c_void_p(-1).value):fail('HANDOVER_PROCESS_SNAPSHOT_FAILED')
        try:
            entry=ProcessEntry();entry.size=C.sizeof(entry);found=k.Process32FirstW(snapshot,C.byref(entry))
            while found and entry.pid!=pid:found=k.Process32NextW(snapshot,C.byref(entry))
            if not found:fail('HANDOVER_PROCESS_PARENT_UNAVAILABLE')
            parent=int(entry.parent)
        finally:k.CloseHandle(snapshot)
        result=dict(pid=pid,created=created,exe=str(release.normal_path(image.value)),cwd=str(cwd),parent=parent)
        if hash_image:result['exe_sha256']=release.file_hash(release.no_links(result['exe']))
        return result
    finally:k.CloseHandle(handle)


def listener_owners(ports):
    values=sorted(set(ports))
    if any(type(p) is not int or not 1<=p<=65535 for p in values):fail('HANDOVER_PORT_INVALID')
    if not values:return {}
    apis()
    script="""
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$p=ConvertFrom-Json ([Console]::In.ReadToEnd())
$r=@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object {$p -contains [int]$_.LocalPort} | Select-Object LocalAddress,LocalPort,OwningProcess)
ConvertTo-Json -InputObject $r -Compress
"""
    result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',script],input=json.dumps(values),capture_output=True,text=True,encoding='utf-8',timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:fail('HANDOVER_LISTENER_QUERY_FAILED')
    rows=json.loads(result.stdout);rows=[rows] if isinstance(rows,dict) else rows;mapping={port:[] for port in values}
    for row in rows:
        port,pid=int(row['LocalPort']),int(row['OwningProcess'])
        if port not in mapping or pid<=0:fail('HANDOVER_LISTENER_RESULT_INVALID')
        mapping[port].append(dict(address=str(row['LocalAddress']),pid=pid))
    return {port:sorted(rows,key=lambda r:(r['address'],r['pid'])) for port,rows in mapping.items()}

def process_parent_map():
    k,_=apis();snapshot=k.CreateToolhelp32Snapshot(2,0)
    if snapshot in (None,C.c_void_p(-1).value):fail('HANDOVER_PROCESS_SNAPSHOT_FAILED')
    try:
        entry=ProcessEntry();entry.size=C.sizeof(entry);found=k.Process32FirstW(snapshot,C.byref(entry));result={}
        while found:
            result[int(entry.pid)]=int(entry.parent);found=k.Process32NextW(snapshot,C.byref(entry))
        return result
    finally:k.CloseHandle(snapshot)


def descendant_identities(pid):
    """All current descendants, excluding stale parent-PID reuse relationships."""
    root=process_identity(pid);parents=process_parent_map();known={pid:root}
    for _ in range(16):
        additions=[]
        for candidate,parent in sorted(parents.items()):
            if candidate in known or parent not in known:continue
            child=process_identity(candidate)
            if child['parent']!=parent:fail('HANDOVER_PROCESS_TREE_CHANGED')
            if int(child['created'])<int(known[parent]['created']):continue
            additions.append(child)
        if not additions:return {str(p):v for p,v in known.items()}
        for child in additions:known[child['pid']]=child
        if len(known)>64:fail('HANDOVER_PROCESS_TREE_TOO_LARGE')
    fail('HANDOVER_PROCESS_TREE_TOO_DEEP')


def trusted_console_host(identity):
    k,_=apis();function=k.GetSystemDirectoryW;function.argtypes=[W.LPWSTR,W.UINT];function.restype=W.UINT
    directory=C.create_unicode_buffer(32768);length=function(directory,len(directory))
    if not 0<length<len(directory):fail('HANDOVER_SYSTEM_DIRECTORY_UNAVAILABLE')
    return Path(identity['exe'])==Path(directory.value)/'conhost.exe'