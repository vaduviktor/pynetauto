import textfsm


def main():
    file = open("outputs/host_cnfp_show_int.txt", encoding='utf-8')
    raw_text_data = file.read()
    file.close()
    print(raw_text_data)

    template = textfsm.TextFSM(open("templates/dnfvi_cnfp_sh_int.textfsm"))
    result = template.ParseText(raw_text_data)

    print(template.header)
    # print(result)

    for a in ([dict(zip(template.header, item)) for item in result]):
        print(a)

    return


if __name__ == "__main__":
    main()
