
import requests
from datetime import date, timedelta, datetime
import json
from statistics import mean
import os
from dotenv import load_dotenv
import schedule
from time import sleep

load_dotenv("./config/.env")
members_list_filename = "./config/members_list.json"
categories_filename = "./config/categories.json"
bot_name = "Gainz Tracker"

class clan:
    def __init__(self, members_list):
        self.clan_list = []
        for member in members_list:
            new_member = clan_member(member)
            self.clan_list.append(new_member)
        pass

    def clan_stats_to_file(self, filename, filetype):
        if filetype == "json":
            dataset = {}
            for member in self.clan_list:
                current_member = member.convert_to_json()
                dataset[current_member["username"]] = current_member["data_set"]
            with open(f"./config/daily_stats/{filename}.{filetype}", "w") as my_file:
                json.dump(dataset, my_file)
                my_file.close()
        elif filetype == "csv":
            dataset = []
            for member in self.clan_list:
                dataset.append(member.convert_to_csv())
            with open(f"./config/daily_stats/{filename}.{filetype}", "w") as my_file:
                my_file.write("\n".join(dataset))
                my_file.close()
        pass

class clan_member:
    def __init__(self, username):
        original_username = username
        while (current_stats:= requests.get(f"https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player={username}")).status_code != 200:
            match current_stats.status_code:
                case 404:
                    how_to_proceed = input(f"Invalid username: {username}, how would you like to proceed?\n1:Update Username\n2:Remove member\n3:Exit\n").replace(" ", "_")
                    match how_to_proceed:
                        case "1":
                            username = input("Please enter updated username.\n")
                        case "2":
                            username = False
                            break
                        case _:
                            username = False
                            break
                case 503:
                    print("Server receiving too many requests, trying again.")
                case _:
                    print(f"Receiveed unknown status code when retrieving highscores for {username}; status code {current_stats.status_code}")
                    return False
        if original_username != username: #now need to update json with updated username
            with open(members_list_filename) as my_file:
                members_list = json.load(my_file)
            if username != False:
                previous_usernames = members_list[original_username]
                previous_usernames.append(original_username)
                members_list[username] = previous_usernames
            del members_list[original_username]
            with open(members_list_filename, "w") as my_file:
                json.dump(members_list, my_file)
                my_file.close()
        if username != False: 
            self.username = username
            self.parse_hiscores_request(current_stats.text)

    def parse_hiscores_request(self, request_text):
        current_stats = request_text.splitlines()
        with open(categories_filename) as my_file:
            skills_list = json.load(my_file)["All"]
        item_number = 0
        for item in skills_list:
            skill_name = item
            try:
                skill_stats = current_stats[item_number].split(',')
            except IndexError:
                print(f"error pulling data for {self.username}")
                break
            if len(skill_stats) == 2:
                skill_rank = int(skill_stats[0])
                skill_score = int(skill_stats[1])
                setattr(self, skill_name.replace(" ", "_").lower(), {"rank" : skill_rank, "score": skill_score})
            else:
                skill_rank = int(skill_stats[0])
                skill_level = int(skill_stats[1])
                skill_xp = int(skill_stats[2])
                setattr(self, skill_name.replace(" ", "_").lower(), {"rank" : skill_rank, "level": skill_level, "xp": skill_xp})
            item_number+=1
        print(f"Successfully pulled stats for username: {self.username}")
        pass

    def convert_to_csv(self):
        data_set = []
        for attr, value in self.__dict__.items():
            if attr != "username":
                data_set.append(f"{self.username},{attr}, {value}")
        return "\n".join(data_set)

    def convert_to_json(self):
        data_set = {}
        for attr, value in self.__dict__.items():
            if attr != "username":
                data_set[attr] = value
        return {"username": self.username, "data_set": data_set}

    def print_skills(self):
        for attr, value in self.__dict__.items():
            print(f"{attr}:{value}")
        pass

class clan_json:
    def __init__(self, json_filepath):
        with open(json_filepath) as my_file:
            self.full_dataset = json.load(my_file)
        with open(categories_filename) as my_file:
            self.skills_list = json.load(my_file)
        self.members_list = []
        for username in self.full_dataset:
            self.members_list.append(username)
        pass

    def get_average(self, skill=None, remove_noattempts=True):
        if skill in self.skills_list["Skills"]:
            group_ranks = []
            group_xps = []
            group_levels = []
            for username in self.full_dataset:
                rank = int(self.full_dataset[username][skill]['rank'])
                if rank == -1:
                    rank = 0
                group_ranks.append(rank)
                group_xps.append(int(self.full_dataset[username][skill]['xp']))
                group_levels.append(int(self.full_dataset[username][skill]['level']))
            group_ranks = round(mean(group_ranks))
            group_xps = round(mean(group_xps))
            group_levels = round(mean(group_levels))
            return {'rank': group_ranks, 'level': group_levels, 'xp': group_xps}
        elif (skill in self.skills_list["Bosses"]) or (skill in self.skills_list["Minigames"]) or (skill in self.skills_list["Clue Scrolls"]):
            group_ranks = []
            group_scores = []
            for username in self.full_dataset:
                rank = int(self.full_dataset[username][skill]['rank'])
                if rank == -1:
                    rank = 0
                if rank != 0:
                    group_ranks.append(rank)
                score = int(self.full_dataset[username][skill]['score'])
                if score == -1:
                    score = 0
                if (remove_noattempts == False) or (score != 0):
                    group_scores.append(score)
            group_ranks = round(mean(group_ranks))
            group_scores = round(mean(group_scores))
            return {'rank':group_ranks,'score':group_scores}
        elif skill == None:
            full_dataset = {}
            for skill_dataset in self.skills_list:
                match skill_dataset:
                    case "Skills":
                        for skill in self.skills_list[skill_dataset]:
                            group_ranks = []
                            group_xps = []
                            group_levels = []
                            for username in self.full_dataset:
                                rank = int(self.full_dataset[username][skill]['rank'])
                                if rank == -1:
                                    rank = 0
                                group_ranks.append(rank)
                                group_xps.append(int(self.full_dataset[username][skill]['xp']))
                                group_levels.append(int(self.full_dataset[username][skill]['level']))
                            group_ranks = round(mean(group_ranks))
                            group_xps = round(mean(group_xps))
                            group_levels = round(mean(group_levels))
                            full_dataset[skill] = {"rank": group_ranks, "level": group_levels, "xp": group_xps}
                    case "Bosses" | "Minigames" | "Clue Scrolls":
                        for skill in self.skills_list[skill_dataset]:
                            group_ranks = []
                            group_scores = []
                            for username in self.full_dataset:
                                rank = int(self.full_dataset[username][skill]['rank'])
                                if rank == -1:
                                    rank = 0
                                if rank != 0:
                                    group_ranks.append(rank)
                                score = int(self.full_dataset[username][skill]['score'])
                                if score == -1:
                                    score = 0
                                if (remove_noattempts == False) or (score != 0):
                                    group_scores.append(score)
                            if len(group_ranks)>0:
                                group_ranks = round(mean(group_ranks))
                            else:
                                group_ranks = 0
                            if len(group_scores)>0:
                                group_scores = round(mean(group_scores))
                            else:
                                group_scores = 0
                            full_dataset[skill] = {"rank":group_ranks,"score":group_scores}
                    case _:
                        pass
            return full_dataset
        else:
            print(f"{skill} is not a valid score to check.")
        pass

    def top_members(self, skill_group, selection=None, amount=False):
        match skill_group:
            case "Skills":
                if amount==False:
                    amount = len(self.members_list)*24
                if selection == None:
                    skill_list = self.skills_list[skill_group]
                elif type(selection)==str:
                    skill_list = [selection]
                else:
                    skill_list = selection
                results = []
                for item in skill_list:
                    scores = []
                    for username in self.members_list:
                        user_score = {
                            "username":username,
                            "skill":item,
                            "rank":self.full_dataset[username][item]["rank"],
                            "level":self.full_dataset[username][item]["level"],
                            "xp":self.full_dataset[username][item]["xp"],
                        }
                        if user_score["xp"]==-1:
                            user_score["xp"]=0
                        scores.append(user_score)
                    scores = sorted(scores, key=lambda d: d['xp'], reverse=True)[:amount]
                    for item in scores:
                        results.append(item)
                if len(results) == amount:
                    return results
                else:
                    results = sorted(results, key=lambda d: d['xp'], reverse=True)[:amount]
                    return results
            case "Bosses" | "Minigames" | "Clue Scrolls":
                if amount==False:
                    amount = len(self.members_list)
                if selection == None:
                    skill_list = self.skills_list[skill_group]
                elif type(selection)==str:
                    skill_list = [selection]
                else:
                    skill_list = selection
                results = []
                for item in skill_list:
                    scores = []
                    for username in self.members_list:
                        user_score = {
                            "username":username,
                            "skill":item,
                            "score":self.full_dataset[username][item]["score"],
                            "rank":self.full_dataset[username][item]["rank"]
                            }
                        if user_score["score"]==-1:
                            user_score["score"]=0
                        scores.append(user_score)
                    scores = sorted(scores, key=lambda d: d['score'], reverse=True)[:amount]
                    #scores = scores[:amount]
                    for item in scores:
                        results.append(item)
                if len(results) == amount:
                    return results
                else:
                    results = sorted(results, key=lambda d: d['score'], reverse=True)[:amount]
                    return results
            case _:
                pass

class discord_commands:
    def __init__(self):
        load_dotenv()
        pass    #if a bot is created in the future, place it in the init here.

    def send_webhook(self, url, payload):
        result = requests.post(url, json = payload)
        try:
            result.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
        else:
            print("Payload delivered successfully, code {}.".format(result.status_code))
        
    def generate_daily_top_skill_earners(self, json_filepath=(f"""./config/daily_stats_comparisons/{(date.today() - timedelta(days = 1)).strftime("%b-%d-%Y")}---{date.today().strftime("%b-%d-%Y")}.json"""), amount=3):
        with open(categories_filename) as my_file:
            skills_list = json.load(my_file)["Skills"]
            skills_list.remove("overall")
            clan_progress_datasheet = clan_json(json_filepath)
            results = clan_progress_datasheet.top_members("Skills", skills_list, amount=amount)
            fields = []
            for index, person in enumerate(results):
                fields.append({
                    "name": f"Rank {index+1}",
                    "value": f"**Username**: {person['username']}\n**Skill**: {person['skill'].title()}\n**XP**: {person['xp']:,}",
                    "inline": False
                })
            post_title = f'Top XP Gained - Daily\n{(date.today() - timedelta(days=1)).strftime("%b %d")} to {date.today().strftime("%b %d")}'
            payload = {
                "username": bot_name,
                "embeds": [
                    {
                        "fields": fields,
                        "title": post_title,
                        "thumbnail": {
                            "url": "https://static.wikia.nocookie.net/ikov-2/images/2/25/Unnamed_(1).png"
                        }
                    }
                ],
                "components": [],
                "content": ""
            }
            self.send_webhook(os.getenv('discord_webhook'), payload)
                                      
def generate_daily_datasheet(filetype="json"):
    with open(members_list_filename) as my_json:
        clan_members = json.load(my_json)
    my_clan = clan(clan_members)
    todays_date = date.today().strftime("%b-%d-%Y")
    if filetype in ["json","csv"]:
        my_clan.clan_stats_to_file(todays_date, filetype)

def generate_comparison_datasheet(previous_day_json=(f"""{(date.today() - timedelta(days = 1)).strftime("%b-%d-%Y")}.json"""), sooner_day_json=(f"""{date.today().strftime("%b-%d-%Y")}.json""")):
    with open(members_list_filename) as my_json:
        clan_members = json.load(my_json)
    with open(f"./config/daily_stats/{previous_day_json}") as my_file:
        spreadsheet1 = json.load(my_file)
        member_list_1 = []
        for member in spreadsheet1:
            member_list_1.append(member)
    with open(f"./config/daily_stats/{sooner_day_json}") as my_file:
        spreadsheet2 = json.load(my_file)
        member_list_2 = []
        for member in spreadsheet2:
            member_list_2.append(member)
    master_member_list = []
    unlocated_members = []
    for person in member_list_2:
        if person in member_list_1:
            master_member_list.append({"old_username":person, "new_username":person})
        else:
            unlocated_members.append(person)
    with open(members_list_filename) as my_json:
        clan_members = json.load(my_json)
    for person in unlocated_members:
        previous_usernames = clan_members[person]
        for previous_username in previous_usernames:
            located=False
            if previous_username in member_list_1:
                master_member_list.append({"old_username":previous_username, "new_username":person})
                located=True
                break
        if located == True:
            continue
        master_member_list.append({"old_username":False, "new_username":person})
    with open(categories_filename) as my_file:
        skills_list = json.load(my_file)
    new_dataset = {}
    for username in master_member_list:
        old_username = username["old_username"]
        new_username = username["new_username"]
        user_dataset = {}
        for skill in skills_list["Skills"]:
            try:
                value1 = spreadsheet1[old_username][skill]
            except KeyError:
                value1 = {
                    "rank": -1,
                    "level": -1,
                    "xp": -1
                }
            value2 = spreadsheet2[new_username][skill]
            rank_difference = int(value1['rank'])-int(value2['rank'])
            level_difference = int(value2['level'])-int(value1['level'])
            xp_difference = int(value2['xp'])-int(value1['xp'])
            new_value = {'rank': rank_difference, 'level': level_difference, 'xp': xp_difference}
            user_dataset[skill] = new_value
        for boss in skills_list["Bosses"]:
            try:
                value1 = spreadsheet1[old_username][boss]
            except KeyError:
                value1 = {
                    "rank": -1,
                    "score": -1
                }
            value2 = spreadsheet2[new_username][boss]
            rank_difference = int(value1['rank'])-int(value2['rank'])
            score_difference = int(value2['score'])-int(value1['score'])
            new_value = {'rank': rank_difference, 'score': score_difference}
            user_dataset[boss] = new_value
        for minigame in skills_list["Minigames"]:
            try:
                value1 = spreadsheet1[old_username][minigame]
            except KeyError:
                value1 = {
                    "rank": -1,
                    "score": -1
                }
            value2 = spreadsheet2[new_username][minigame]
            rank_difference = int(value1['rank'])-int(value2['rank'])
            score_difference = int(value2['score'])-int(value1['score'])
            new_value = {'rank': rank_difference, 'score': score_difference}
            user_dataset[minigame] = new_value
        for clue in skills_list["Clue Scrolls"]:
            try:
                value1 = spreadsheet1[old_username][clue]
            except KeyError:
                value1 = {
                    "rank": -1,
                    "score": -1
                }
            value2 = spreadsheet2[new_username][clue]
            rank_difference = int(value1['rank'])-int(value2['rank'])
            score_difference = int(value2['score'])-int(value1['score'])
            new_value = {'rank': rank_difference, 'score': score_difference}
            user_dataset[clue] = new_value
        new_dataset[new_username] = user_dataset
    new_filename = "./config/daily_stats_comparisons/" + previous_day_json[:previous_day_json.find('.json')]+'---'+sooner_day_json[:sooner_day_json.find('.json')]+'.json'
    with open(new_filename, "w") as my_file:
        json.dump(new_dataset, my_file)
        my_file.close()    
    pass

if __name__ == "__main__":
    my_discord = discord_commands()
    schedule.every().day.at("12:00").do(generate_daily_datasheet)
    schedule.every().day.at("12:05").do(generate_comparison_datasheet)
    schedule.every().day.at("12:10").do(my_discord.generate_daily_top_skill_earners)
    while True:
        schedule.run_pending()
        print(f"Current time is {datetime.now().strftime('%H:%M:%S')}, sleeping for 60 seconds.")
        sleep(60)