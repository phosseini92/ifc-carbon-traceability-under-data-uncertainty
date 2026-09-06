"""Full IFC schema/EXPRESS check; pytest is needed by IfcOpenShell's rule executor."""
from pathlib import Path
import json
import ifcopenshell
import ifcopenshell.validate

if __name__=='__main__':
    root=Path(__file__).parent
    model=ifcopenshell.open(str(root/'inputs/controlled_shell.ifc'))
    logger=ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model,logger,express_rules=True)
    # IFC entities are stringified for a portable validation record.
    (root/'docs/ifc_schema_validation.json').write_text(json.dumps(logger.statements,indent=2,default=str))
    print(f'IFC schema / EXPRESS findings: {len(logger.statements)}')
    raise SystemExit(1 if logger.statements else 0)
