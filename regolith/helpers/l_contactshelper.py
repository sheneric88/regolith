"""Helper for finding and listing contacts from the contacts.yml database.
Prints name, institution, and email (if applicable) of the contact.
"""
import dateutil
import dateutil.parser as date_parser
from regolith.dates import (
    is_current,
    get_dates
)
from regolith.helpers.basehelper import SoutHelperBase
from regolith.fsclient import _id_key
from regolith.tools import (
    all_docs_from_collection,
    get_pi_id,
    fragment_retrieval,
    search_collection,
    key_value_pair_filter,
    collection_str
)

TARGET_COLL = "contacts"
HELPER_TARGET = "l_contacts"


def subparser(subpi):
    subpi.add_argument(
        "run",
        help='run the lister. To see allowed optional arguments, type "regolith helper l_contacts"')
    subpi.add_argument(
        "-n",
        "--name",
        help='name or name fragment (single argument only) to use to find contacts')
    subpi.add_argument(
        "-i",
        "--inst",
        help='institution or an institution fragment (single argument only) to use to find contacts')
    subpi.add_argument(
        "-d",
        "--date",
        help='approximate date in ISO format (YYYY-MM-DD) corresponding to when the contact was entered in the database. Comes with a default range of 4 months centered around the date; change range using --range argument')
    subpi.add_argument(
        "-r",
        "--range",
        help='range (in months) centered around date d specified by --date, i.e. (d +/- r/2)',
        default=4)
    subpi.add_argument(
        "-o",
        "--notes",
        help='fragment (single argument only) to be found in the notes section of a contact'
    )
    subpi.add_argument(
        "-f",
        "--filter",
        nargs="+",
        help='Search this collection by giving key element pairs'
    )
    subpi.add_argument(
        "-k",
        "--keys",
        nargs="+",
        help='Specify what keys to return values from when running --filter. If no argument is given the default is just the id.'
    )
    return subpi


def stringify(con):
    return f"name: {con.get('name')}, institution: {con.get('institution')}, email: {con.get('email', 'missing')}"


class ContactsListerHelper(SoutHelperBase):
    """Helper for finding and listing contacts from the contacts.yml file
    """
    # btype must be the same as helper target in helper.py
    btype = HELPER_TARGET
    needed_dbs = [f'{TARGET_COLL}']

    def construct_global_ctx(self):
        """Constructs the global context"""
        super().construct_global_ctx()
        gtx = self.gtx
        rc = self.rc
        if "groups" in self.needed_dbs:
            rc.pi_id = get_pi_id(rc)
        rc.coll = f"{TARGET_COLL}"
        try:
            if not rc.database:
                rc.database = rc.databases[0]["name"]
        except BaseException:
            pass
        colls = [
            sorted(
                all_docs_from_collection(rc.client, collname), key=_id_key
            )
            for collname in self.needed_dbs
        ]
        for db, coll in zip(self.needed_dbs, colls):
            gtx[db] = coll
        gtx["all_docs_from_collection"] = all_docs_from_collection
        gtx["float"] = float
        gtx["str"] = str
        gtx["zip"] = zip

    def sout(self):
        rc = self.rc
        if rc.filter:
            collection = key_value_pair_filter(self.gtx["contacts"], rc.filter)
        else:
            collection = self.gtx["contacts"]
        def_l = set(stringify(i) for i in
                    self.gtx['contacts'])
        if rc.name:
            namel = set(stringify(i) for i in
                        fragment_retrieval(
                            collection, [
                                "_id", "aka", "name"], rc.name))
        else:
            namel = def_l
        if rc.inst:
            instl = set(stringify(i) for i in
                        fragment_retrieval(
                            collection,
                            ["institution"],
                            rc.inst))
        else:
            instl = def_l
        if rc.notes:
            notel = set(stringify(i) for i in
                        fragment_retrieval(
                            collection, [
                                "notes"], rc.notes))
        else:
            notel = def_l
        if rc.date:
            date_list = []
            temp_dat = date_parser.parse(rc.date).date()
            temp_dict = {
                "begin_date": (temp_dat -
                               dateutil.relativedelta.relativedelta(
                                   months=int(
                                       rc.range))).isoformat(),
                "end_date": (temp_dat +
                             dateutil.relativedelta.relativedelta(
                                 months=int(
                                     rc.range))).isoformat()}
            for contact in collection:
                curr_d = get_dates(contact)['date']
                if is_current(temp_dict, now=curr_d):
                    date_list.append(stringify(contact))
            datel = set(date_list)
        else:
            datel = def_l
        res_l = set.intersection(namel, instl, notel, datel)
        if rc.keys:
            results = (collection_str(res_l, rc.keys))
            print(results, end="")
            return
        for item in res_l:
            print(item)
        return
