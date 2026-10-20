import React from 'react';
import {DATCOV02} from '../ui-preview/company/DATCOV02';
import {mountPortal} from './session';
import {useBusinessContext} from './context';
import {useCompanyWorkflow} from './workflow';
import type {PortalIdentity} from './types';
function Portal({session,onLogout}:{session:PortalIdentity;onLogout:()=>void}){const business=useBusinessContext(session),workflow=useCompanyWorkflow(business,session);return <DATCOV02 session={session} onLogout={onLogout} business={business} workflow={workflow}/>;}
mountPortal((session,onLogout)=><Portal session={session} onLogout={onLogout}/>);
