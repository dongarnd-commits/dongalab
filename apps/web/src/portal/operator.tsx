import React from 'react';
import {mountPortal} from './session';
import OperatorIntake from './operator-intake';
mountPortal((session,onLogout)=><OperatorIntake session={session} onLogout={onLogout}/>);
