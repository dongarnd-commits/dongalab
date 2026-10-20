import {DATCOV02} from '../ui-preview/company/DATCOV02';
import {mountPortal} from './session';
mountPortal((session,onLogout)=><DATCOV02 session={session} onLogout={onLogout}/>);
