import React from 'react';
import {DATCOV02} from '../ui-preview/company/DATCOV02';
import {mountPortal} from './session';
import {useBusinessContext} from './context';
import type {PortalIdentity} from './types';
function Portal({session,onLogout}:{session:PortalIdentity;onLogout:()=>void}){const business=useBusinessContext(session);return <DATCOV02 session={session} onLogout={onLogout} business={business}/>;}
mountPortal((session,onLogout)=><Portal session={session} onLogout={onLogout}/>);
