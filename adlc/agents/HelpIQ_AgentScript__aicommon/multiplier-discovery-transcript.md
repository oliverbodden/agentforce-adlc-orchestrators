# Multiplier Discovery Session — 2026-05-13

**Participants:** Oliver Bodden (HelpIQ engineer), Dario Sanchez (Support Ops / IAM bridge), Chris Bopp (HelpIQ internals), Anthony Miguel (Support Ops, organizer)

**Purpose:** Walk through the JSM "Request Access to Software" portal flow and identify what HelpIQ should mirror in its software-access conversation.

---

## Raw transcript

> Light cleanup only — speakers identified, timestamps preserved. Verbatim content.

**Oliver Bodden** (00:56) — "Good. Sorry I'm late. And thanks, Anthony, for setting this up. So, can we just get started?"

**Anthony Miguel** (01:05) — "Yeah, I think so. I just want to introduce y'all to Dario. He's also part of the Support Ops team. He helps out with a lot of the X provisioning for our… bridges the gap between our IAM team as well as Support Ops, so I think he would be the right person to help address the questions that you have with regards to accesses to softwares. And just accesses in general."

**Oliver Bodden** (01:27) — "Well, hey, Dario, nice to meet you. So yeah, we wanted to get some insights into the process. We have specific questions, but I think maybe just in general, like, if we want to make… because you're probably familiar with HelpIQ, I think I've seen your name on some of the reviews. So we're trying to make sure we have, like, the right experience for HelpIQ to self-serve software access requests. But there's a lot of nuances on, like, is it for you? Is it for someone else? Is it for multiple people? Is it in a different environment? Or maybe a different app than the one you're asking for. And right now, the help IQ doesn't have that context unless it's able to pull it from knowledge. So I think the goal will be to just understand that thought process on, hey, I need a request, and come up with a lot of, like, the scenarios that you think about, like, oh, first I look at this, I ask these follow-up questions, based on this software, I know this is different. You know, whatever you can share along those lines would be useful."

**Dario Sanchez** (02:36) — "Yeah, absolutely. So, we do have a list of a lot of software, right? A lot of it is actually owned by IT, but there are some other types that are not owned by us, right? And they usually have, like, their own documentation for it. In terms of the software that we do have, we've been trying to make it… or to have documentation for it, stating, you know, what is needed when the software is being requested. And I think we've been pretty good of closing those gaps and creating new documentation. In fact, I've been helping with that as well. I've created documentation, and it's all going into the ITKB, which help IQ pulls information from it. Now, in terms of submitting the request, if we go to the software, or the request software access page in the JSM portal..."

**Oliver Bodden** (03:42) — "Do you want to share your screen and just walk through it in case you're doing it?"

**Dario Sanchez** (03:45) — "Absolutely. So we do have a couple ways to request software. We have the regular JSM portal, which can be accessed by going to the Indeed's Help Center, and it takes you to this site, and we go into IT Services. Then we do the Software and System Access. Here, you click Request Access, and then you will find pages of software that you can request access to, and there is also an Other option. A lot of this software is actually provisioned automatically, in a way that you submit the software, the owner of that specific application approves it, and then it's just granted to you automatically. There is no interaction, or a service desk tech does not have to actually touch the ticket, because it's all automatically done. Let's say I come and pick one of the options, fill it, let's just give an example — Adobe. The moment I go to Adobe, it opens up a new option saying, you know, what is it that you're requesting, or what type of license?"

**Oliver Bodden** (05:42) — "Sorry for jumping in. That bottom section changes based on the app that you're picking?"

**Dario Sanchez** (05:45) — "Correct, yes. So if I go to Backstage, for instance, it doesn't have that option. If I go to Adobe, of course, there is an option right here. Same thing would happen for Office — there is different types of licenses for that. So it changes, and it varies depending on the license that you're requesting access to. Like, for instance, Figma is another one of those — you need viewer, editor, collaborator, developer. And this also pairs up with information that we have in documentation."

**Dario Sanchez** (06:52) — *(walks through Confluence ITKB → Account and Access → Request Access articles, shows Figma article that explains license types and points back to the JSM portal)*

**Dario Sanchez** (07:17) — "This basically gives you a walkthrough of what you have to do. In this case, it explains what Figma is, the type of licenses that we have, and the steps to access or request a license. You go into the site I just showed, you select, you search for Figma, and you select the license that you need. The license will be granted to you. You'll need approval by the application owner. So Daryl Shaw would manage this Figma request. It is like that for a lot of the software that we have. Once again, you would just come in here, request the access, and a lot of it is automated. Those that are not automated, the ticket ends up landing in the service desk queue, and one of our techs actions it depending on what is being asked."

**Oliver Bodden** (08:33) — "And those subfields, those are stored in the JSM ticket in a specific field. Like, when you pick Adobe, or Figma, then you pick one of these — that's stored in a specific field in JSM that is then pushed to Okta, or however we do the provisioning?"

**Dario Sanchez** (08:54) — "Correct."

**Oliver Bodden** (08:55) — "Okay, and that field is the same whether it's Figma or another? It's the same field, we're just putting different values on the same field?"

**Dario Sanchez** (09:02) — *(walks through searching for Figma tickets in JSM, shows automated provisioning where the request closes itself once the owner approves)*

**Oliver Bodden** (10:46) — "Okay, so it seems like that structure of having the line and then request details underneath, that's critical to make sure the automation works. … So that means that the user identifies the right application, they pick it, the UI is smart enough to ask questions that are needed to provision them automatically. And then that happens in the UI as a drop-down. They pick it, they submit. Okay. I have another question, but do you have more details to go over about what you have so far?"

**Dario Sanchez** (11:39) — "As we change from app to app, the dropdown just changes depending on what type of access you are requesting. As I mentioned, a lot of these are solved by Multiplier. And very few — one of our techs has to action them manually, meaning we get the request, we have documentation that says if we get someone — for instance, like Marketo — once we get those, we have documentation stating where we are supposed to put this person who is requesting access to this type of application."

**Oliver Bodden** (12:23) — "Got it, okay. Chris, do you know if HelpIQ already does follow-up questions to confirm the type of things, or that's something we have to check?"

**Chris Bopp** (12:33) — "So, as far as I'm aware, the only follow-up question that would be asked in this scenario, if someone says, hey, I want Figma, would be, what's your reason for wanting Figma? So it goes out and says, okay, they're asking for Figma. It basically does a lookup to get the access key, and so then it has Figma and the access key, and the reason it's being requested, and it goes out and creates the JSM multiplier. So it doesn't do any of this additional — like, you know, we're seeing there's variation upon the specific license type you can request. I was jotting down some other notes, like, I saw an urgency field. I don't think it gets into any of that today. It's just getting the ID associated with the application being requested, and then one follow-up question, like, what's your reasoning?"

**Dario Sanchez** (13:34) — "Yeah, that usually happens, like, is there a business case for this. Some applications are more strict than others because of licensing issues, and we have a set pool of licenses, and we don't want to go above that. Or we want this specific software to be for a specific group of people. For instance, there is one that it's only for Japan. I was working on documentation for that the other day that stated, you know, if you are in Japan, you need to request this. If you're not in Japan, this is not for you."

**Dario Sanchez** (14:28) — "Another thing that I wanted to add, and I don't know if this is relevant: we have two fields. This is the field of the person that is requesting, and then there is the field of if you're requesting on behalf of somebody. We see this happen very often. Like, I am a manager, I want to request this on behalf of my team, on my teammate. What we've seen many times is that I put this, but then — let's say I already have access to Datadog. I put this, requesting access for John. And then you submit the request, but then Multiplier is not reading these. Multiplier's reading: okay, who is the person requesting? So Multiplier goes, like, wait a second, you already have access to Datadog. So then the ticket has to be reopened, and the tech has to add it to the right person. That is an issue we usually have here and there, of requesting on behalf of somebody else."

**Oliver Bodden** (15:33) — "And this is something I wanted to try and improve with the next version of HelpIQ. So then — but you have to be able to add the LDAP that's used. Like, if they just type Dario Sanchez, to resolve that, right?"

**Dario Sanchez** (15:51) — "Yeah, so if you type right here, it's on the database already. It will pull my LDAP. If, of course, you're not here, then that means you're not in the company. There's no John Smith — there's no options."

**Chris Bopp** (16:10) — "Do contractors show up under there?"

**Dario Sanchez** (16:13) — "Yeah."

**Chris Bopp** (16:14) — "They have an Indeed account?"

**Dario Sanchez** (16:15) — "Correct. This is a colleague of ours, he is a contractor, and he is right here."

**Oliver Bodden** (16:24) — "What about if it's more than one person? You have to do it manually? Automation wouldn't work?"

**Dario Sanchez** (16:30) — "Yep. We had that very clear example a few days ago for Data Lake. Data Lake is one of those applications handled by the CDER team, and it is clearly stated that if you need access to Data Lake, you need to submit your own request, or your manager do it on your behalf. Now, we had someone who came with a list of, like, 20 people. We need to add or do, like, a bulk add. We couldn't, because first, there is not an option here to do a bulk add. So that wasn't possible. Data Lake is also another group that, because it handles a lot of sensitive data, it has to be checked. We don't have access, or the group is not visible in Okta for us to just add someone to it. The group is hidden."

**Oliver Bodden** (17:38) — "Can you so you can pick Data Lake here? But when you submit it for one person, who checks if they have access? Oh, that goes to the person to approve it, right?"

**Dario Sanchez** (17:52) — "It goes to the person to approve. If I pick here, you know, Data Lake, this automation will generate a ticket. And then if we check right here, all the requests right here, the automation basically as you to this group."

**Oliver Bodden** (18:25) — "I see. But that happens in the Multiplier app, right? Not — they take care of it."

**Dario Sanchez** (18:30) — "They take care of it. Now, for that specific person, that specific example I just mentioned, where we needed to add bulk people, we weren't able to do this because this group is hidden. But there are other groups that, if you need a bulk add for, let's say Gong, or Adobe — we have the ability to do that, but that one will have to be done manually. That one cannot be automated, because we don't have an option. Could we have one? Possibly. But I don't know if we have explored that option yet."

**Oliver Bodden** (19:08) — "And then you mentioned Japan. So when somebody picks that app that's only for Japan, anybody can see it in JSM, but the person who approves it is responsible for saying no, for rejecting it because you're not in Japan?"

**Dario Sanchez** (19:28) — "Correct."

**Dario Sanchez** (19:30) — "Yep, I think it was Concur. *(navigates to Concur article)* This guy walks us through Request Concur in this travel and expense platform from Japan. It's primarily used for Japan, you go under this, and then if we go here and try to request access for Concur, it wouldn't say there is no option for me saying, oh, are you based in Japan? Or, are you a Japanese user? No. The request will go through, and then it is up to the person who approves it to either approve it or not, or to check if that person is based in Japan."

**Oliver Bodden** (20:50) — "Okay, so if we can get HelpIQ to find the article first, that could be a solution where we tell them, hey, are you in Japan? Or something that could happen. Just thinking out loud."

**Oliver Bodden** (20:59) — "What about, any questions? Chris or Anthony? Good so far?"

**Chris Bopp** (21:12) — "I just think related to that question there — like, if HelpIQ can find the article. There's also in my, I was just thinking, like, how often are these being ingested into Data360 for the retriever to have access. So if you're creating this new article, like, you just created one yesterday, someone comes and asks about it, they might get a miss, because it doesn't even exist in the knowledge base. So, frequency of how often that data is being re-ingested is a question."

**Dario Sanchez** (21:45) — "I think there was a period — and I've always asked this — there's a period of time in between when an article is put into our knowledge base, and HelpIQ gets to read it. I know it's not immediately, because I've tested that, and it usually takes a couple days. So it would be nice to have an exact set of, like, oh, it takes 2 days, 1 day, 3 hours."

**Anthony Miguel** (22:12) — "Just in response to that, we can do that ad hoc, we just need to let Parth and Sidude know, but typically it would be, like, every about a week it would do the sync, but if it's something that's important, we can do it ad hoc."

**Oliver Bodden** (22:35) — "How — so, are articles updated, like, constantly? Daily? Or…"

**Dario Sanchez** (22:41) — "Not really. I wouldn't say daily, it's just that they're basically on the go. If there is changes in the way it's being requested, or changes on the person who approves it, or changes — for instance, there was one I was working on, Zendesk. When I created this document, I noted, hey, by the way, this application is going to be deprecated soon. Once it's deprecated, I'll just delete the document."

**Oliver Bodden** (23:18) — "One more question — figuring out which app to click on. How often do you see people picking the wrong app?"

**Dario Sanchez** (23:30) — "Almost never."

**Oliver Bodden** (23:31) — "Oh, almost never?"

**Dario Sanchez** (23:32) — "Yeah, but I don't think I've seen anybody saying, oh, I requested the wrong thing. When people come here, or when they're requesting access, they're pretty good about that. They know what they want. Saying, like, I requested the wrong request? Rarely. Very low percent — probably below 5."

**Oliver Bodden** (23:55) — "Because I saw sometimes they're very similar. But maybe those are random. Like, Tableau has 3."

**Dario Sanchez** (24:05) — "But you have a bunch of other options. This is Tableau Japan, JP, and this is Tableau with Scaled Ops. I've never seen anybody requesting the wrong thing."

**Oliver Bodden** (24:21) — "Okay. I'm curious, because I mean, here they can search and find the app, read, and pick it. On HelpIQ, they're just chatting. So I wonder how much people, because of this UI, they're able to pick it. I don't have the data enough to know if it's a problem, I was just curious. I think the big difference is they have a very clean UI, they can click, and if they see 3 options, maybe they Slack somebody, hey, which one is it that I need? They pick the right one, versus in HelpIQ, they're just saying it, and hopefully HelpIQ picks the right one."

**Chris Bopp** (24:55) — "That's a good question, Oliver. I don't know today how that works. If someone's requested, say, Adcentral, if it goes to look it up, what is it gonna come back with, assuming these are 3 separate identified keys? It might just pick the first one it pulls back. It doesn't narrow it down. And the other thing — I was looking at when the JSM ticket gets created for Multiplier. Today, there's no concept of request on behalf of. It just populates 'raise on behalf of'. So raise is me. On behalf of is if we're doing it for someone else."

**Dario Sanchez** (25:34) — "Yep, instead of saying my name, it would say the name of the person that is being requested on behalf of."

**Oliver Bodden** (25:44) — "Yeah, I think that's gonna be something we'll have to add to the prompt. At least those high-level decisions, and then I'm also curious on request details, because that seems to be pretty critical for the creation of the automation. Those are two things — request on behalf of, asking discovery questions, hey, is this for you, for someone else? Little things like that. And then I'm also curious on how we pick the app. If they say something — they put the name, they write it — how do we make sure we're picking the right, specific one when we actually send everything?"

**Oliver Bodden** (26:36) — "I'm thinking about the fact of — if somebody sends an app, they type an app — Multiplier only returns. Not all apps are on Multiplier, right, on that view?"

**Dario Sanchez** (26:51) — "So not all the apps are in here, and not all the apps are automated."

**Oliver Bodden** (26:56) — "Okay."

**Dario Sanchez** (26:57) — "That's a list that I do not have, but we could — there was a list that was being kept, but I don't think it's very up to date anymore. We could probably talk to our software team to give us that. We have a lot of the applications here. Not all of them, and that's why there is an Other. And not all of these are automated. As you can see, Data Lake was a clear example. A lot of these are unassigned because there's no need for a tech — solves automatically. But if the request is, let's say, Other..."

**Dario Sanchez** (27:48) — *(walks through a non-automated request example showing tech intervention and the documentation that drives it)*

**Oliver Bodden** (29:29) — "I know we're at time, but this is extremely helpful. Anthony, this is your meeting? If you can share the recording when you get it, I'll make some sort of a document explaining our understanding, just to align, see if there's something we're missing. We're going to use that to update the prompt in the software one, to make sure it follows this kind of mental model."

**Dario Sanchez** (29:54) — "I'm glad I could help. Any questions or anything else, you guys can always let me know. Always happy to help."

---

## Source

Recording from Anthony Miguel's meeting on 2026-05-13. Speakers: Chris Bopp, Anthony Miguel, Oliver Bodden, Dario Sanchez.
