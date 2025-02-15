"""
Provides linkedin api-related code
"""
import random
import logging
from time import sleep
from urllib.parse import urlencode
import json
import re

from linkedin_api.utils.helpers import get_id_from_urn

from linkedin_api.client_sales_navigator import Client

logger = logging.getLogger(__name__)


def default_evade():
    """
    A catch-all method to try and evade suspension from Linkedin.
    Currenly, just delays the request by a random (bounded) time
    """
    sleep(random.uniform(0, 0))  # sleep a random duration to try and evade suspention


class Linkedin(object):
    """
    Class for accessing Linkedin API.
    """

    _MAX_UPDATE_COUNT = 100  # max seems to be 100
    _MAX_SEARCH_COUNT = 49  # max seems to be 49
    _MAX_REPEATED_REQUESTS = (
        200
    )  # VERY conservative max requests count to avoid rate-limit

    def __init__(self, username, password, refresh_cookies=False, debug=False):
        self.client = Client(refresh_cookies=refresh_cookies, debug=debug)
        self.client.authenticate(username, password)
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)

        self.logger = logger

    def _fetch(self, uri, evade=default_evade, **kwargs):
        """
        GET request to Linkedin API
        """
        evade()

        url = f"{self.client.API_BASE_URL}{uri}"
        return self.client.session.get(url, **kwargs)

    def _post(self, uri, evade=default_evade, **kwargs):
        """
        POST request to Linkedin API
        """
        evade()

        url = f"{self.client.API_BASE_URL}{uri}"
        return self.client.session.post(url, **kwargs)

    def get_current_profile(self):
        """
        GET current profile
        """
        response = self._fetch(
            f'/me/', headers={"accept": "application/vnd.linkedin.normalized+json+2.1"})
        data = response.json()

        profile = {
            'firstName': data['included'][0]['firstName'],
            'lastName': data['included'][0]['lastName'],
            'publicIdentifier': data['included'][0]['publicIdentifier'],
            'occupation': data['included'][0]['occupation'],
            'message_id': data['included'][0]['entityUrn'].split(':')[3],
        }

        try:
            profile['avatarUrl'] = data['included'][0]['picture']['rootUrl'] + \
                data['included'][0]['picture']['artifacts'][2]['fileIdentifyingUrlPathSegment']
        except TypeError:
            profile['avatarUrl'] = None

        return profile

    def search(self, params, limit=None, results=[]):
        """
        Do a search.
        """
        count = (
            limit
            if limit and limit <= Linkedin._MAX_SEARCH_COUNT
            else Linkedin._MAX_SEARCH_COUNT
        )
        default_params = {
            "count": str(count),
            "filters": "List()",
            "origin": "GLOBAL_SEARCH_HEADER",
            "q": "all",
            "start": len(results),
            "queryContext": "List(spellCorrectionEnabled->true,relatedSearchesEnabled->true,kcardTypes->PROFILE|COMPANY)",
        }

        default_params.update(params)

        res = self._fetch(
            f"/search/blended?{urlencode(default_params)}",
            headers={"accept": "application/vnd.linkedin.normalized+json+2.1"},
        )

        data = res.json()

        new_elements = []
        for i in range(len(data["data"]["elements"])):
            new_elements.extend(data["data"]["elements"][i]["elements"])
            # not entirely sure what extendedElements generally refers to - keyword search gives back a single job?
            # new_elements.extend(data["data"]["elements"][i]["extendedElements"])

        results.extend(new_elements)
        results = results[
            :limit
        ]  # always trim results, no matter what the request returns

        # recursive base case
        if (
            limit is not None
            and (
                len(results) >= limit  # if our results exceed set limit
                or len(results) / count >= Linkedin._MAX_REPEATED_REQUESTS
            )
        ) or len(new_elements) == 0:
            return results

        self.logger.debug(f"results grew to {len(results)}")

        return self.search(params, results=results, limit=limit)

    def search_voyager(self, limit=None, results=[], start=0, keys=None, industries=None,  profileLanguages=None,
                       networkDepth=None, title="", firstName="", lastName="", currentCompanies=None, schools=None, regions=None, past_companies=None, 
                       company=None, school=None, connection_of=None):
        """
        Default search
        """
        count = (
            limit
            if limit and limit <= Linkedin._MAX_SEARCH_COUNT
            else Linkedin._MAX_SEARCH_COUNT
        )

        default_params = {
            "count": '10',
            "filters": "List()",
            "origin": "CLUSTER_EXPANSION",
            "q": "all",
            "start": str(start),
            "queryContext": "List(spellCorrectionEnabled->true,relatedSearchesEnabled->true,kcardTypes->PROFILE|COMPANY)",
        }

        if past_companies is None:
            default_params["past_companies"] = ""
        else:
            default_params["origin"] = "FACETED_SEARCH"
            default_params["past_companies"] = "pastCompany->{},".format("|".join(past_companies))

        if networkDepth is None:
            default_params['network_depth'] = ""
        else:
            default_params["origin"] = "FACETED_SEARCH"
            default_params["network_depth"] = "network->{},".format("|".join(networkDepth))

        if connection_of is None: 
            default_params['connection_of'] = ""
        else:
            default_params["origin"] = "FACETED_SEARCH"
            default_params["connection_of"] = "connectionOf->{},".format("|".join(connection_of))

        if profileLanguages is None:
            default_params['profileLanguages'] = ""
        else:            
            default_params["origin"] = "FACETED_SEARCH"
            default_params["profileLanguages"] = "profileLanguage->{},".format("|".join(profileLanguages))
            
        if regions is None:
            default_params["regions"] = ""
        else:
            default_params["origin"] = "FACETED_SEARCH"
            default_params["regions"] = "geoRegion->{},".format("|".join(regions))

        if keys is None:
            default_params["keys"] = ""
        else:
            default_params["origin"] = "FACETED_SEARCH"
            default_params["keys"] = keys


        if industries is None:
            default_params["industries"] = ""
        else: 
        
            default_params["origin"] = "FACETED_SEARCH"
            default_params["industries"] = "industry->{},".format("|".join(industries)) 

        if title:
            default_params['title'] = ",title->{}".format(title)
            default_params["origin"] = "FACETED_SEARCH"
        else:
            default_params["title"] = ""

        if firstName:
            default_params['firstName'] = ",firstName->{}".format(
                firstName)
            default_params["origin"]="FACETED_SEARCH"
        else:
            default_params["firstName"]=""

        if lastName:
            default_params['lastName']=",lastName->{}".format(lastName)
            default_params["origin"]="FACETED_SEARCH"
        else:
            default_params["lastName"]=""

        if currentCompanies is None:
            default_params["currentCompanies"]=""
        else:
            default_params['currentCompanies']=",currentCompany->{}".format("|".join(currentCompanies))
            default_params["origin"]="FACETED_SEARCH"
            

        if schools is None:
            default_params["schools"]=""
        else:
            default_params['schools']=",school->{}".format("|".join(schools))
            default_params["origin"]="FACETED_SEARCH" 
            

        if company is None:
            default_params["company"] = ""
        else:
            default_params["company"] = ",company->{}".format(company)
            default_params["origin"]="FACETED_SEARCH"

        if school is None:
            default_params["school"] = ""
        else:
            default_params["school"] = ",school->{}".format(school)
            default_params["origin"]="FACETED_SEARCH"

        res=self._fetch(
            # f"/search/blended?{urlencode(default_params)}",
            f"/search/blended?count=10&filters=List("+ default_params["connection_of"] 
            + default_params["past_companies"] + default_params["regions"] + default_params['industries'] +
             default_params['network_depth'] +
            default_params['profileLanguages'] + "resultType-%3EPEOPLE" + default_params["school"] + default_params["company"]  + default_params["firstName"] +
            default_params["lastName"] + default_params["title"] + default_params["currentCompanies"] +
            default_params["schools"] + ")&keywords=" + default_params['keys'] + "%20&origin=" +
            default_params["origin"] + "&q=all&queryContext=List(spellCorrectionEnabled-%3Etrue,relatedSearchesEnabled-%3Etrue)&start=" +
            default_params['start'],
            headers = {
                "accept": "application/vnd.linkedin.normalized+json+2.1"},
        )
        data=res.json()
        
        try: 
            if not data.get("data").get("paging").get("total"):
                return {}
        except AttributeError:
            return {}

        new_elements=[]
        for i in range(len(data["data"]["elements"])):
            new_elements.extend(data["data"]["elements"][i]["elements"])
        # not entirely sure what extendedElements generally refers to - keyword search gives back a single job?
        # new_elements.extend(data["data"]["elements"][i]["extendedElements"])

        results.extend(new_elements)
        results=results[
            : limit
        ]  # always trim results, no matter what the request returns

        # recursive base case
        if (
            limit is not None
            and (
                len(results) >= limit  # if our results exceed set limit
                or len(results) / count >= Linkedin._MAX_REPEATED_REQUESTS
            )
        ) or len(new_elements) == 0:
            return results

        self.logger.debug(f"results grew to {len(results)}")

        return data

    def search_people(
        self,
        keywords = None,
        connection_of = None,
        networkDepth = None,
        currentCompanies = None,
        past_companies = None,
        nonprofit_interests = None,
        profileLanguages = None,
        regions = None,
        industries = None,
        schools = None,
        # profiles without a public id, "Linkedin Member"
        include_private_profiles = False,
        limit = None,
        start = None,
        keys = None,
        title = "",
        firstName = "",
        lastName = "", 
        company = None,
        school=None 
    ):
        """
        Do a people search.
        """

        data=self.search_voyager(limit = limit, results = [], start = start,
                                   keys = keywords, industries = industries,  profileLanguages = profileLanguages,
                                   networkDepth = networkDepth, title = title, firstName = firstName,
                                   lastName = lastName, currentCompanies = currentCompanies, schools = schools, regions = regions, past_companies=past_companies, 
                                   company=company, school=school, connection_of=connection_of)

        if not data:
            return []

        try:
            fullData=data.get("data").get("elements")
        except AttributeError:
            return []

        data=data.get("included")

        results=[]
        for item in data:
            if "publicIdentifier" not in item:
                continue

            if item.get("occupation"):
                occupation=item.get("occupation")
                size=len(occupation.split("\u2013"))
                if size == 2:
                    occupation=occupation.split("\u2013")
                    position=occupation[0]
                    company=occupation[1]
                else:
                    size=len(occupation.split(" at "))
                    if size == 2:
                        occupation=occupation.split(" at ")
                        position=occupation[0]
                        company=occupation[1]
                    else:
                        size=len(occupation.split("|"))
                        if size == 2:
                            occupation=occupation.split("|")
                            position=occupation[0]
                            company=occupation[1]
                        else:
                            size=len(occupation.split("-"))
                            if size == 2:
                                occupation=occupation.split("-")
                                position=occupation[0]
                                company=occupation[1]
                            else:
                                position=occupation
                                company=""

            try:
                displayPictureUrl=item.get("picture").get(
                    "rootUrl") + item.get("picture").get("artifacts")[0].get("fileIdentifyingUrlPathSegment")
            except AttributeError:
                displayPictureUrl = ""

            results.append(
                {
                    "urn_id": item.get("entityUrn").split(":")[3],
                    "public_id": item.get("publicIdentifier"),
                    "first_name": item.get("firstName"),
                    "last_name": item.get("lastName"),
                    "position": position,
                    "company": company,
                    "displayPictureUrl": displayPictureUrl
                }
            )

            results = results[:10]
            pos = 0
            for element in fullData[0].get("elements"):
                results[pos]['location'] = element.get("subline").get("text")
                results[pos]['navigation_url'] = "https://www.linkedin.com/in/" + \
                    results[pos].get("public_id")
                pos += 1

                if pos > (len(results) - 1):
                    break

        return results


    def get_current_profile_connections(self, start=None):
    
        res = self._fetch(
            f'/search/blended?count=10&filters=List(network-%3EF,resultType-%3EPEOPLE)&origin=MEMBER_PROFILE_CANNED_SEARCH&q=all&queryContext=List(spellCorrectionEnabled-%3Etrue,relatedSearchesEnabled-%3Etrue)&start=' + str(start),
            headers = {
                "accept": "application/vnd.linkedin.normalized+json+2.1"},
        )

        data = res.json()

        print(json.dumps(data, indent=4))

        data = data.get("included")[10:]

        return data

    def get_quantity_of_current_profile_connections(self):
        res = self._fetch(
            f'/search/blended?count=10&filters=List(network-%3EF,resultType-%3EPEOPLE)&origin=MEMBER_PROFILE_CANNED_SEARCH&q=all&queryContext=List(spellCorrectionEnabled-%3Etrue,relatedSearchesEnabled-%3Etrue)&start=0',
            headers = {
                "accept": "application/vnd.linkedin.normalized+json+2.1"},
        )

        data = res.json()

        count_of_connections = data.get("data").get("metadata").get("totalResultCount")

        return count_of_connections


    def get_profile_contact_info(self, public_id=None, urn_id=None):
        """
        Return data for a single profile.

        [public_id] - public identifier i.e. tom-quirk-1928345
        [urn_id] - id provided by the related URN
        """
        res = self._fetch(
            f"/identity/profiles/{public_id or urn_id}/profileContactInfo"
        )
        data = res.json()

        contact_info = {
            "email_address": data.get("emailAddress"),
            "websites": [],
            "twitter": data.get("twitterHandles"),
            "birthdate": data.get("birthDateOn"),
            "ims": data.get("ims"),
            "phone_numbers": data.get("phoneNumbers", []),
        }

        websites = data.get("websites", [])
        for item in websites:
            if "com.linkedin.voyager.identity.profile.StandardWebsite" in item["type"]:
                item["label"] = item["type"][
                    "com.linkedin.voyager.identity.profile.StandardWebsite"
                ]["category"]
            elif "" in item["type"]:
                item["label"] = item["type"][
                    "com.linkedin.voyager.identity.profile.CustomWebsite"
                ]["label"]

            del item["type"]

        contact_info["websites"] = websites

        return contact_info

    def get_profile_skills(self, public_id=None, urn_id=None):
        """
        Return the skills of a profile.

        [public_id] - public identifier i.e. tom-quirk-1928345
        [urn_id] - id provided by the related URN
        """
        params = {"count": 100, "start": 0}
        res = self._fetch(
            f"/identity/profiles/{public_id or urn_id}/skills", params=params
        )
        data = res.json()

        skills = data.get("elements", [])
        for item in skills:
            del item["entityUrn"]

        return skills

    def get_profile(self, public_id=None, urn_id=None):
        """
        Return data for a single profile.

        [public_id] - public identifier i.e. tom-quirk-1928345
        [urn_id] - id provided by the related URN
        """
        res = self._fetch(
            f"/identity/profiles/{public_id or urn_id}/profileView")

        data = res.json()
        if data and "status" in data and data["status"] != 200:
            self.logger.info("request failed: {}".format(data["message"]))
            return {}

        # massage [profile] data

        profile = data["profile"]

        try:
            avatarUrl = data.get("profile").get('miniProfile').get('picture').get(
                'com.linkedin.common.VectorImage').get('artifacts')[0].get('fileIdentifyingUrlPathSegment')
        except AttributeError:
            avatarUrl = ""

        if "miniProfile" in profile:
            if "picture" in profile["miniProfile"]:
                profile["displayPictureUrl"] = profile["miniProfile"]["picture"][
                    "com.linkedin.common.VectorImage"
                ]["rootUrl"] + avatarUrl
            profile["profile_id"] = get_id_from_urn(
                profile["miniProfile"]["entityUrn"])

            del profile["miniProfile"]

        del profile["defaultLocale"]
        del profile["supportedLocales"]
        del profile["versionTag"]
        del profile["showEducationOnProfileTopCard"]

        # massage [experience] data
        experience = data["positionView"]["elements"]
        for item in experience:
            if "company" in item and "miniCompany" in item["company"]:
                if "logo" in item["company"]["miniCompany"]:
                    logo = item["company"]["miniCompany"]["logo"].get(
                        "com.linkedin.common.VectorImage"
                    )
                    if logo:
                        item["companyLogoUrl"] = logo["rootUrl"]
                del item["company"]["miniCompany"]

        profile["experience"] = experience

        # massage [skills] data
        # skills = [item["name"] for item in data["skillView"]["elements"]]
        # profile["skills"] = skills

        profile["skills"] = self.get_profile_skills(
            public_id=public_id, urn_id=urn_id)

        # massage [education] data
        education = data["educationView"]["elements"]
        for item in education:
            if "school" in item:
                if "logo" in item["school"]:
                    item["school"]["logoUrl"] = item["school"]["logo"][
                        "com.linkedin.common.VectorImage"
                    ]["rootUrl"]
                    del item["school"]["logo"]

        profile["education"] = education

        return profile

    def get_profile_connections(self, urn_id):
        """
        Return a list of profile ids connected to profile of given [urn_id]
        """
        return self.search_people(connection_of=urn_id, networkDepth="F")

    def get_company_updates(
        self, public_id=None, urn_id=None, max_results=None, results=[]
    ):
        """"
        Return a list of company posts

        [public_id] - public identifier ie - microsoft
        [urn_id] - id provided by the related URN
        """
        params = {
            "companyUniversalName": {public_id or urn_id},
            "q": "companyFeedByUniversalName",
            "moduleKey": "member-share",
            "count": Linkedin._MAX_UPDATE_COUNT,
            "start": len(results),
        }

        res = self._fetch(f"/feed/updates", params=params)

        data = res.json()

        if (
            len(data["elements"]) == 0
            or (max_results is not None and len(results) >= max_results)
            or (
                max_results is not None
                and len(results) / max_results >= Linkedin._MAX_REPEATED_REQUESTS
            )
        ):
            return results

        results.extend(data["elements"])
        self.logger.debug(f"results grew: {len(results)}")

        return self.get_company_updates(
            public_id=public_id, urn_id=urn_id, results=results, max_results=max_results
        )

    def get_profile_updates(
        self, public_id=None, urn_id=None, max_results=None, results=[]
    ):
        """"
        Return a list of profile posts

        [public_id] - public identifier i.e. tom-quirk-1928345
        [urn_id] - id provided by the related URN
        """
        params = {
            "profileId": {public_id or urn_id},
            "q": "memberShareFeed",
            "moduleKey": "member-share",
            "count": Linkedin._MAX_UPDATE_COUNT,
            "start": len(results),
        }

        res = self._fetch(f"/feed/updates", params=params)

        data = res.json()

        if (
            len(data["elements"]) == 0
            or (max_results is not None and len(results) >= max_results)
            or (
                max_results is not None
                and len(results) / max_results >= Linkedin._MAX_REPEATED_REQUESTS
            )
        ):
            return results

        results.extend(data["elements"])
        self.logger.debug(f"results grew: {len(results)}")

        return self.get_profile_updates(
            public_id=public_id, urn_id=urn_id, results=results, max_results=max_results
        )

    def get_current_profile_views(self):
        """
        Get profile view statistics, including chart data.
        """
        res = self._fetch(f"/identity/wvmpCards")

        data = res.json()

        return data["elements"][0]["value"][
            "com.linkedin.voyager.identity.me.wvmpOverview.WvmpViewersCard"
        ]["insightCards"][0]["value"][
            "com.linkedin.voyager.identity.me.wvmpOverview.WvmpSummaryInsightCard"
        ][
            "numViews"
        ]

    def get_school(self, public_id):
        """
        Return data for a single school.

        [public_id] - public identifier i.e. uq
        """
        params = {
            "decorationId": "com.linkedin.voyager.deco.organization.web.WebFullCompanyMain-12",
            "q": "universalName",
            "universalName": public_id,
        }

        res = self._fetch(f"/organization/companies?{urlencode(params)}")

        data = res.json()

        if data and "status" in data and data["status"] != 200:
            self.logger.info("request failed: {}".format(data))
            return {}

        school = data["elements"][0]

        return school

    def get_company(self, public_id):
        """
        Return data for a single company.

        [public_id] - public identifier i.e. univeristy-of-queensland
        """
        params = {
            "decorationId": "com.linkedin.voyager.deco.organization.web.WebFullCompanyMain-12",
            "q": "universalName",
            "universalName": public_id,
        }

        res = self._fetch(f"/organization/companies", params=params)

        data = res.json()

        if data and "status" in data and data["status"] != 200:
            self.logger.info("request failed: {}".format(data["message"]))
            return {}

        company = data["elements"][0]

        return company

    def get_conversation_details(self, profile_urn_id):
        """
        Return the conversation (or "message thread") details for a given [public_profile_id]
        """
        # passing `params` doesn't work properly, think it's to do with List().
        # Might be a bug in `requests`?
        res = self._fetch(
            f"/messaging/conversations?\
            keyVersion=LEGACY_INBOX&q=participants&recipients=List({profile_urn_id})"
        )

        data = res.json()

        item = data["elements"][0]
        item["id"] = get_id_from_urn(item["entityUrn"])

        return item

    def get_conversations(self):
        """
        Return list of conversations the user is in.
        """
        params = {"keyVersion": "LEGACY_INBOX"}

        res = self._fetch(f"/messaging/conversations", params=params)

        return res.json()

    def get_conversation(self, conversation_urn_id):
        """
        Return the full conversation at a given [conversation_urn_id]
        """
        res = self._fetch(
            f"/messaging/conversations/{conversation_urn_id}/events")

        return res.json()

    def send_message(self, conversation_urn_id=None, recipients=[], message_body=None):
        """
        Send a message to a given conversation. If error, return true.

        Recipients: List of profile urn id's
        """
        params = {"action": "create"}

        if not (conversation_urn_id or recipients) and not message_body:
            return True

        message_event = {
            "eventCreate": {
                "value": {
                    "com.linkedin.voyager.messaging.create.MessageCreate": {
                        "body": message_body,
                        "attachments": [],
                        "attributedBody": {"text": message_body, "attributes": []},
                        "mediaAttachments": [],
                    }
                }
            }
        }

        if conversation_urn_id and not recipients:
            res = self._post(
                f"/messaging/conversations/{conversation_urn_id}/events",
                params=params,
                data=json.dumps(message_event),
            )
        elif recipients and not conversation_urn_id:
            message_event["recipients"] = recipients
            message_event["subtype"] = "MEMBER_TO_MEMBER"
            payload = {
                "keyVersion": "LEGACY_INBOX",
                "conversationCreate": message_event,
            }
            res = self._post(
                f"/messaging/conversations", params=params, data=json.dumps(payload)
            )

        return res.status_code != 201

    def mark_conversation_as_seen(self, conversation_urn_id):
        """
        Send seen to a given conversation. If error, return True.
        """
        payload = json.dumps({"patch": {"$set": {"read": True}}})

        res = self._post(
            f"/messaging/conversations/{conversation_urn_id}", data=payload
        )

        return res.status_code != 200

    def get_user_profile(self):
        """"
        Return current user profile
        """
        sleep(
            random.randint(0, 1)
        )  # sleep a random duration to try and evade suspention

        res = self._fetch(f"/me")

        data = res.json()

        return data

    def get_invitations(self, start=0, limit=3):
        """
        Return list of new invites
        """
        params = {
            "start": start,
            "count": limit,
            "includeInsights": True,
            "q": "receivedInvitation"
        }

        res = self.client.session.get(
            f"{self.client.API_BASE_URL}/relationships/invitationViews",
            params=params
        )

        if res.status_code != 200:
            return []

        response_payload = res.json()
        return [element["invitation"] for element in response_payload["elements"]]

    def reply_invitation(self, invitation_entity_urn, invitation_shared_secret, action="accept"):
        """
        Reply to an invite, the default is to accept the invitation.
        @Param: invitation_entity_urn: str
        @Param: invitation_shared_secret: str
        @Param: action: "accept" or "ignore"
        Returns True if sucess, False otherwise
        """
        invitation_id = get_id_from_urn(invitation_entity_urn)
        params = {
            'action': action
        }
        payload = json.dumps({
            "invitationId": invitation_id,
            "invitationSharedSecret": invitation_shared_secret,
            "isGenericInvitation": False
        })

        res = self.client.session.post(
            f"{self.client.API_BASE_URL}/relationships/invitations/{invitation_id}",
            params=params,
            data=payload
        )

        return res.status_code == 200

    def add_connection(self, profile_urn_id, message=None):
        data = '{"trackingId":"yvzykVorToqcOuvtxjSFMg==","invitations":[],"excludeInvitations":[],"invitee":{"com.linkedin.voyager.growth.invitation.InviteeProfile":{"profileId":' + \
            '"' + profile_urn_id + '"' + '}}}'
        if message:
            data = '{"trackingId":"yvzykVorToqcOuvtxjSFMg==","invitations":[],"excludeInvitations":[],"invitee":{"com.linkedin.voyager.growth.invitation.InviteeProfile":{"profileId":' + \
                '"' + profile_urn_id + '"' + '}},"message":' '"' + message + '"' + '}'

        res = self._post(
            '/growth/normInvitations',
            data=data,
            headers={"accept": "application/vnd.linkedin.normalized+json+2.1"},
        )
        return res.status_code

    def remove_connection(self, public_profile_id):
        res = self._post(
            f"/identity/profiles/{public_profile_id}/profileActions?action=disconnect",
            
        )

        return res.status_code != 200

    def get_typehead(self, keywords=None, type=None):

        res = self._fetch(
            f'/typeahead/hitsV2?keywords=' + keywords + '&origin=OTHER&q=type&type=' + type,
            headers={"accept": "application/vnd.linkedin.normalized+json+2.1"
        })

        data = res.json()

        elements = data.get("data").get("elements")

        return elements


    def try_sales_navigator(self):

        res = self._fetch(
            f'/salesApiPeopleSearch?q=peopleSearchQuery&start=0&count=25&query=(doFetchHeroCard:true,keywords:python,recentSearchParam:(doLogHistory:true),searchHistoryParam:(doLogHistory:true),spotlightParam:(selectedType:ALL),doFetchFilters:true,doFetchHits:true,doFetchSpotlights:true)&decoration=%28degree%2CentityUrn%2CfirstName%2ClastName%2CfullName%2CobjectUrn%2CgeoRegion%2Chighlight%28com.linkedin.sales.profile.profileHighlights.MentionedInTheNewsHighlight!_nt%3Dcom.linkedin.sales.deco.common.profile.highlights.DecoratedMentionedInTheNewsHighlight%28articleName%2Ccount%2Csource%2Curl%29%2Ccom.linkedin.sales.profile.profileHighlights.ProfileHighlights!_nt%3Dcom.linkedin.sales.deco.common.profile.highlights.DecoratedProfileHighlights%28sharedConnection%28sharedConnectionUrns*~fs_salesProfile%28entityUrn%2CfirstName%2ClastName%2CfullName%2CpictureInfo%2CprofilePictureDisplayImage%2CpresenceStatus%29%29%2CteamlinkInfo%28totalCount%29%2CsharedEducations*%28overlapInfo%2CentityUrn~fs_salesSchool%28entityUrn%2ClogoId%2Cname%2Curl%2CschoolPictureDisplayImage%29%29%2CsharedExperiences*%28overlapInfo%2CentityUrn~fs_salesCompany%28companyPictureDisplayImage%2CentityUrn%2Cname%2CpictureInfo%29%29%2CsharedGroups*%28entityUrn~fs_salesGroup%28entityUrn%2Cname%2ClargeLogoId%2CsmallLogoId%2CgroupPictureDisplayImage%29%29%29%2Ccom.linkedin.sales.profile.profileHighlights.RecentPositionChangeHighlight!_nt%3Dcom.linkedin.sales.deco.common.profile.highlights.DecoratedRecentPositionChangeHighlight%28companyUrn%2CcompanyName%2Cduration%2Ctitle%29%29%2CteamlinkIntrosHighlight%2CopenLink%2Cpremium%2Cteamlink%2CpendingInvitation%2CprofilePictureDisplayImage%2Cviewed%2Csaved%2CcrmStatus%2CtrackingId%2CrecommendedLeadTrackingId%2ClistCount%2CcurrentPositions*%2Ctags*%2CpastPositions*%2CmatchedArticles*%2CfacePiles*%2CsharedConnectionsHighlight%28count%29%29',
            headers={"accept": "application/vnd.linkedin.normalized+json+2.1"}
        )

        import ipdb; ipdb.set_trace()

        data = res.json()

        return data 

    
