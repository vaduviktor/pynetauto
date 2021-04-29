from nornir import InitNornir
from nornir.core.plugins.inventory import InventoryPluginRegister
from custom_inventory import ExcelInventory


def main_task(task):

    print(task.host.hostname)

    print(task.host.password)

    return


def main():

    InventoryPluginRegister.register("ExcelInventory", ExcelInventory)
    nr = InitNornir(
        runner={
            "plugin": "threaded",
            "options": {
                "num_workers": 100,
            },
        },
        inventory={"plugin": "ExcelInventory",
                   "options": {
                       "excel_filename" : "SwitchList.xlsx"
                   }}
    )

    nr.run(name="test", task=main_task)

    # import ipdb; ipdb.set_trace()

    return


if __name__ == "__main__":
    main()
