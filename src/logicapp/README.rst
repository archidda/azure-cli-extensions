Commands for working with Azure Logicapp
==============================================

# Basic Usage

Run operation on the logic app site:
.. code:: 
    az logicapp show -g aaaaarchidda --name disableTest 
    az logicapp start -g aaaaarchidda --name disableTest 
    az logicapp stop -g aaaaarchidda --name disableTest 
    az logicapp restart -g aaaaarchidda --name disableTest 
    az logicapp delete -g aaaaarchidda --name disableTest 
    az logicapp update -g aaaaarchidda --name disableTest --set enabled=true 