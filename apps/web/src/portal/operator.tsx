import React from 'react';
import OperatorPortal from '../ui-preview/operator/OperatorPortal';
import {mountPortal} from './session';
import {useBusinessContext} from './context';
import type {PortalIdentity} from './types';
function Portal({session,onLogout}:{session:PortalIdentity;onLogout:()=>void}){const business=useBusinessContext(session);return <OperatorPortal session={session} onLogout={onLogout} business={business}/>;}
mountPortal((session,onLogout)=><Portal session={session} onLogout={onLogout}/>);
