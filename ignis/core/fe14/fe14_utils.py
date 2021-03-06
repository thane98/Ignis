import ctypes
import os

from ignis.model.fe14_route import FE14Route

from ignis.model.weapon_exp import WeaponExp
from ignis.model.weapon_rank import WeaponRank


_SKILL_FIELDS = ["skill_1", "skill_2", "skill_3", "skill_4", "skill_5"]


def nerf_character(gd, rid):
    fields = [("bases", 10, 1, -5), ("growths", 10, 5, 0)]
    for field_id, k, step_size, limit in fields:
        stats = list(map(lambda b: ctypes.c_int8(b).value, gd.bytes(rid, field_id)))
        for _ in range(0, k):
            if stats[1] > limit:
                stats[1] -= step_size
        gd.set_bytes(
            rid, field_id, bytes(map(lambda b: ctypes.c_uint8(b).value, stats))
        )


def get_equipped_skill_names(gd, skills, char_rid):
    equipped_skills = []
    for field in _SKILL_FIELDS:
        skill_rid = gd.rid(char_rid, field)
        if skill_rid != skills.default_skill():
            if name := gd.display(skill_rid):
                equipped_skills.append(name)
    return equipped_skills


def get_route_file(gd, base_path, route, filename, localized=False):
    if route == FE14Route.BIRTHRIGHT:
        route_dir = "A"
    elif route == FE14Route.CONQUEST:
        route_dir = "B"
    elif route == FE14Route.REVELATION:
        route_dir = "C"
    else:
        route_dir = None
    if route_dir:
        path = os.path.join(base_path, route_dir, filename)
        return path if gd.file_exists(path, localized) else None
    else:
        return None


def get_all_files(gd, base_path, ext, chapters, localized=False):
    files = []
    for route, cid in chapters.enabled_chapters():
        filename = cid[4:] + ext
        if route_path := get_route_file(gd, base_path, route, filename, localized):
            files.append(route_path)
        else:
            path = os.path.join(base_path, filename)
            if gd.file_exists(path, localized):
                files.append(path)
    return files


def apply_randomized_skills(gd, characters, user_config, skills, aid, rid):
    personal_skill = None
    if user_config.randomize_personal_skills:
        personal_skill = characters.get_character_personal_skill(aid)
        gd.set_rid(rid, "personal_skill_normal", personal_skill)
        gd.set_rid(rid, "personal_skill_hard", personal_skill)
        gd.set_rid(rid, "personal_skill_lunatic", personal_skill)
    if user_config.randomize_equip_skills:
        character_skills = {personal_skill}
        for field in _SKILL_FIELDS:
            skill_rid = gd.rid(rid, field)
            if skill_rid != skills.default_skill():
                new_skill = skills.random_equip_skill()
                while new_skill in character_skills:
                    new_skill = skills.random_equip_skill()
                character_skills.add(new_skill)
                gd.set_rid(rid, field, new_skill)


def apply_randomized_class_set(
    gd,
    characters,
    classes,
    aid,
    rid,
    ranks_source,
    rand,
    gender=None,
    class_level=None,
    staff_only_ban=False,
):
    original_primary_class = gd.rid(ranks_source, "class_1")

    c1, c2, r1, r2 = characters.get_character_class_set(
        aid, gender, class_level, staff_only_ban
    )
    gd.set_rid(rid, "class_1", c1)
    gd.set_rid(rid, "class_2", c2)
    gd.set_rid(rid, "reclass_1", r1)
    gd.set_rid(rid, "reclass_2", r2)

    # Edge case: Increase the character's level by 20 if going from
    # regular promoted class to one that's capped at 40.
    if classes.is_advanced_class(
        original_primary_class
    ) and not classes.is_capped_at_40_class(original_primary_class):
        if classes.is_capped_at_40_class(c1):
            gd.set_int(rid, "level", gd.int(rid, "level") + 20)

    # Reconcile character and primary class weapon ranks
    class_weapon_ranks = list(enumerate(WeaponRank.ranks_from_fates_job(gd, c1)))
    character_weapon_exp = WeaponExp.from_fates_character(gd, ranks_source)

    # Sort highest rank/exp to lowest
    sorted_class_ranks = sorted(
        class_weapon_ranks,
        key=lambda p: (p[1].sort_value() if p[1] else -1, rand.random()),
        reverse=True,
    )
    sorted_character_exp = sorted(
        character_weapon_exp,
        key=lambda p: (p.sort_value(), rand.random()),
        reverse=True,
    )

    # Transfer highest character weapon exp to corresponding highest for the class
    new_exp = [0] * len(sorted_character_exp)
    for i in range(0, len(sorted_character_exp)):
        index, _ = sorted_class_ranks[i]
        new_exp[index] = sorted_character_exp[i].exp
    WeaponExp.save_fates_weapon_exp(gd, rid, new_exp)


def apply_randomized_bitflags(gd, characters, aid, rid1, rid2):
    bitflags = characters.get_character_bitflags(aid, rid1, rid2)
    for field, value in bitflags.items():
        gd.set_int(rid1, field, value)


def apply_randomized_stats(
    gd, rand, source_rid, destination_rid, strategy, passes, weights=None
):
    gd.set_bytes(
        destination_rid,
        "bases",
        strategy.randomize_stats(
            rand,
            gd.bytes(source_rid, "bases"),
            limits=(-5, 100),
            passes=passes,
            weights=weights,
        ),
    )
    gd.set_bytes(
        destination_rid,
        "growths",
        strategy.randomize_stats(
            rand,
            gd.bytes(source_rid, "growths"),
            limits=(0, 95),
            step_size=5,
            passes=passes,
            weights=weights,
        ),
    )
    gd.set_bytes(
        destination_rid,
        "modifiers",
        strategy.randomize_stats(
            rand,
            gd.bytes(source_rid, "modifiers"),
            limits=(-3, 3),
            passes=passes,
            weights=weights,
        ),
    )


def morph_character(gd, source_rid, destination_rid):
    gd.set_string(destination_rid, "fid", gd.string(source_rid, "fid"))
    gd.set_string(destination_rid, "aid", gd.string(source_rid, "aid"))
    gd.set_string(destination_rid, "name", gd.string(source_rid, "name"))
    gd.set_string(destination_rid, "description", gd.string(source_rid, "description"))
    gd.set_int(destination_rid, "body_type", gd.int(source_rid, "body_type"))
