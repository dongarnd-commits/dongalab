import {createRoot} from "react-dom/client";
import OperatorPortal from "./OperatorPortal";
import type {Company} from "./OperatorPortal";
import fixture from "./operatorFixture.json";
createRoot(document.getElementById("root")!).render(<OperatorPortal examples={fixture.companies as unknown as Company[]}/>);
