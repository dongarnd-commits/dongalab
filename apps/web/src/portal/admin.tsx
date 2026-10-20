import AdminPortal from '../ui-preview/admin/AdminPortal';
import {mountPortal} from './session';
mountPortal((session,onLogout)=><AdminPortal session={session} onLogout={onLogout}/>);
