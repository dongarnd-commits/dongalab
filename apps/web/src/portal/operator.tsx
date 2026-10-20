import OperatorPortal from '../ui-preview/operator/OperatorPortal';
import {mountPortal} from './session';
mountPortal((session,onLogout)=><OperatorPortal session={session} onLogout={onLogout}/>);
