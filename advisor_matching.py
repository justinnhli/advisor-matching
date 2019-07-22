#!/usr/bin/env python

# pylint: disable = bad-continuation

from collections import namedtuple, defaultdict
from csv import DictReader, DictWriter
from pathlib import Path
from random import Random

from gooey import Gooey, GooeyParser


class Professor:

    def __init__(self, row_dict, divisions, args):
        try:
            self.oxy_id = row_dict[args.professor_id]
            self.first_name = row_dict[args.professor_first]
            self.last_name = row_dict[args.professor_last]
            self.department = row_dict[args.professor_dept]
            self.advisee_limit = int(row_dict[args.professor_limit])
        except KeyError as err:
            raise KeyError(' '.join([
                f'Professors file {args.professors_file}',
                f'does not have a column named "{err.args[0]}"',
                f'Available columns are: {", ".join(sorted(row_dict.keys()))}',
            ]))
        if self.department not in divisions:
            print(' '.join([
                f'WARNING: Professor {self.first_name} {self.last_name}',
                f'has a department {self.department}',
                f'that is not in the divisions file {args.divisions_file}',
            ]))

    def __lt__(self, other):
        return self.oxy_id < other.oxy_id

    def __hash__(self):
        return hash(self.oxy_id)

    def __str__(self):
        return self.first_name + ' ' + self.last_name


class Student:

    def __init__(self, row_dict, divisions, args):
        try:
            self.oxy_id = row_dict[args.student_id]
            self.first_name = row_dict[args.student_first]
            self.last_name = row_dict[args.student_last]
            self.username = row_dict[args.student_username]
            self.majors = set(
                major.strip() for major
                in row_dict[args.student_majors].split(args.program_delimiter)
                if major.strip()
            )
        except KeyError as err:
            raise KeyError(' '.join([
                f'Students file {args.students_file}',
                f'does not have a column named "{err.args[0]}"',
                f'Available columns are: {", ".join(sorted(row_dict.keys()))}',
            ]))
        for major in self.majors:
            if major not in divisions:
                print(' '.join([
                    f'WARNING: Student {self.first_name} {self.last_name}',
                    f'has a major {major}',
                    f'that is not in the divisions file {args.divisions_file}.',
                    'Make sure that the majors are separated by a {args.program_delimiter} !',
                ]))
        self.minors = set()
        '''
        self.minors = set(
            minor.strip()
            for minor in row_dict['Minors_Spec_Prepro_Programs'].split(',')
            if minor.strip()
        )
        if all((minor in self.minors) for minor in ['Gender', 'Women', 'and Sexuality Studies Minor']):
            for minor in ['Gender', 'Women', 'and Sexuality Studies Minor']:
                self.minors.remove(minor)
            self.minors.add('Gender, Women, and Sexuality Studies Minor')
        assert all((minor in DIVISIONS) for minor in self.minors), set(self.minors) - set(DIVISIONS.keys())
        '''

    def __lt__(self, other):
        return self.oxy_id < other.oxy_id

    def __hash__(self):
        return hash(self.oxy_id)

    def __str__(self):
        return self.first_name + ' ' + self.last_name


Match = namedtuple('Match', 'professor, student, score, reasons')

def unbuffered_print(s):
    print(s, flush=True)

@Gooey(tabbed_groups=True, default_size=(800, 600))
def create_arg_parser():
    arg_parser = GooeyParser()
    # input/output files
    group = arg_parser.add_argument_group('Input/Output', gooey_options={'columns': 1})
    group.add_argument(dest='divisions_file', widget='FileChooser', help=(
        'The CSV with division information. '
        'The CSV must have the columns specified in the Division Columns tab.'
    ))
    group.add_argument(dest='professors_file', widget='FileChooser', help=(
        'The CSV with professor information. '
        'The CSV must have the columns specified in the Professor Columns tab.'
    ))
    group.add_argument(dest='students_file', widget='FileChooser', help=(
        'The CSV with student information.'
        'The CSV must have the columns specified in the Student Columns tab.'
    ))
    group.add_argument(dest='output_dir', default='~/Desktop/', widget='DirChooser',
        help='The folder to put the output.csv',
    )
    # divisions data
    group = arg_parser.add_argument_group('Division Columns', gooey_options={'columns': 1})
    group.add_argument('--division-program', default='Program',
        help='The name of the column with the major/minor/other programs.',
    )
    group.add_argument('--division-division', default='Division',
        help='The name of the column with the division of each program.',
    )
    # professors data
    group = arg_parser.add_argument_group('Professor Columns', gooey_options={'columns': 1})
    group.add_argument('--professor-id', default='ID Number',
        help='The name of the column with the professor IDs.',
    )
    group.add_argument('--professor-first', default='First Name',
        help='The name of the column with the professor first names.',
    )
    group.add_argument('--professor-last', default='Last Name',
        help='The name of the column with the professor last names.',
    )
    group.add_argument('--professor-dept', default='Department',
        help='The name of the column with the professor departments.',
    )
    group.add_argument('--professor-limit', default='AssignLimit',
        help='The name of the column with the professor max assignments.',
    )
    # students data
    group = arg_parser.add_argument_group('Student Columns', gooey_options={'columns': 1})
    group.add_argument('--student-id', default='ID Number',
        help='The name of the column with the student IDs.',
    )
    group.add_argument('--student-first', default='First Name',
        help='The name of the column with the student first names.',
    )
    group.add_argument('--student-last', default='Last Name',
        help='The name of the column with the student last names.',
    )
    group.add_argument('--student-username', default='Username',
        help='The name of the column with the student usernames.',
    )
    group.add_argument('--student-majors', default='Majors',
        help='The name of the column with the student majors.',
    )
    group.add_argument('--program-delimiter', default=',',
        help='The punctuation used to delimit multiple majors/minors.',
    )
    # matching options
    group = arg_parser.add_argument_group('Matching Options', gooey_options={'columns': 1})
    group.add_argument('--max-new-advisees', default=10, type=int,
        help='The maximum number of new advisees for a faculty.',
    )
    # advanced options
    group = arg_parser.add_argument_group('Advanced Options', gooey_options={'columns': 1})
    group.add_argument('--random-seed', default=8675309, type=int,
        help='The random seed for the search. Using the same number will always give the same results.',
    )
    group.add_argument('--num-trials', default=3, type=int,
        help='The number of matches to try. A larger number will take longer but have "better" results.',
    )
    # return the result
    return arg_parser


def parse_args():
    arg_parser = create_arg_parser()
    args = arg_parser.parse_args()
    args.divisions_file = Path(args.divisions_file).expanduser().resolve()
    args.professors_file = Path(args.professors_file).expanduser().resolve()
    args.students_file = Path(args.students_file).expanduser().resolve()
    args.output_dir = Path(args.output_dir).expanduser().resolve()
    args.output_path = args.output_dir.joinpath('advisor-matching-output.csv')
    if args.output_path.exists():
        raise FileExistsError(' '.join([
            f'Output file {args.output_path} already exists.',
            'Please delete/rename the file before running again.',
        ]))
    return args


def read_divisions(args):
    divisions = {}
    try:
        with args.divisions_file.open() as fd:
            for row in DictReader(fd):
                divisions[row[args.division_program]] = row[args.division_division]
    except KeyError as err:
        raise KeyError(' '.join([
            f'Divisions file {args.divisions_file}',
            f'does not have a column named "{err.args[0]}".',
        ]))
    unbuffered_print(f'INFO: Read data for {len(divisions)} divisions.')
    return divisions


def read_professors(divisions, args):
    professors = []
    with args.professors_file.open() as fd:
        for row in DictReader(fd):
            professors.append(Professor(row, divisions, args))
    unbuffered_print(f'INFO: Read data for {len(professors)} professors.')
    return professors


def read_students(divisions, args):
    students = []
    with args.students_file.open() as fd:
        for row in DictReader(fd):
            students.append(Student(row, divisions, args))
    unbuffered_print(f'INFO: Read data for {len(students)} students.')
    return students


def random_restart_hillclimbing(divisions, professors, students, args):
    best_match = None
    best_score = 0
    rng = Random(args.random_seed)
    for trial_num in range(1, args.num_trials + 1):
        unbuffered_print(f'INFO: Running trial {trial_num} of {args.num_trials}...')
        matches = hillclimb(divisions, professors, students, rng, args)
        total_score = sum(sum(match.score for match in prof_matches) for prof_matches in matches.values())
        if total_score > best_score:
            best_match = matches
            best_score = total_score
        unbuffered_print(f'    Score: {best_score}')
    return best_match


def hillclimb(divisions, professors, students, rng, args):
    # initialize search variables
    num_matched = 0
    matches = defaultdict(set) # Professor -> set[Match]
    potential_matches = []

    # populate all possible matches
    for professor in sorted(professors):
        for student in sorted(students):
            score, reasons = score_match(divisions, professor, student)
            potential_matches.append(Match(professor, student, score, reasons))

    # hill climb on the matches
    while num_matched < len(students):

        # find the best matches
        best_matches = []
        best_score = 0
        for match in potential_matches:
            if match.score > best_score:
                best_matches = [match]
                best_score = match.score
            elif match.score == best_score:
                best_matches.append(match)

        # randomly pick from the best
        if not best_matches:
            raise Exception('No best match found, which should not be possible')
        best_match = rng.choice(best_matches)

        # record the match
        matched_professor = best_match.professor
        matches[matched_professor].add(best_match)

        # remove invalidated matches
        potential_matches.remove(best_match)
        potential_matches = [
            match for match in potential_matches
            if match.student != best_match.student
        ]
        professor_full = (
            (len(matches[matched_professor]) >= args.max_new_advisees) or
            (len(matches[matched_professor]) >= matched_professor.advisee_limit)
        )
        if professor_full:
            potential_matches = [
                match for match in potential_matches
                if match.professor != best_match.professor
            ]

        num_matched += 1

    matched_students = set.union(*(
        set(match.student for match in prof_matches)
        for prof_matches in matches.values()
    ))

    # check that all students are assigned
    assert set(students) == set(matched_students), '\n'.join([
        'Unmatched students:',
        *(
            f'   {student.first_name} {student.last_name} ({student.majors})'
            for student in (set(matched_students) - set(students))
        ),
    ])
    # check that no professors are over limit
    assert not any(
        len(matches[professor]) > professor.advisee_limit
        for professor in professors
    ), list(
        (professor.last_name, professor.advisee_limit, len(matches[professor]))
        for professor in professors
        if len(matches[professor]) > professor.advisee_limit
    )
    return matches


def score_match(divisions, professor, student):
    score = 0
    reasons = []
    major_divisions = set()
    for major in student.majors:
        if professor.department == major:
            score += 1
            reasons.append(f'Student interested in {major} major')
        if major in divisions:
            major_divisions.add(divisions[major])
    for minor in student.minors:
        if professor.department == minor:
            score += 0.75
            reasons.append(f'Student interested in {minor} minor')
    if divisions[professor.department] in major_divisions:
        score += 0.25
        reasons.append(f'Student interested in majors in {divisions[professor.department]} division')
    return score, tuple(reasons)


def save_results(best_matches, output_path):
    # save matches to file FIXME
    columns = [
        'Student ID',
        'Student First Name',
        'Student Last Name',
        'Student Username',
        'Student Majors',
        'Advisor ID',
        'Advisor First Name',
        'Advisor Last Name',
        'Advisor Remaining Capacity',
        'Reasons',
    ]
    with open(output_path, 'w') as fd:
        writer = DictWriter(fd, fieldnames=columns)
        writer.writeheader()
        for professor, matches in best_matches.items():
            for match in matches:
                reasons = '\n'.join(match.reasons)
                majors = ', '.join(match.student.majors)
                writer.writerow({
                    'Student ID': f'{match.student.oxy_id}',
                    'Student First Name': f'{match.student.first_name}',
                    'Student Last Name': f'{match.student.last_name}',
                    'Student Username': f'{match.student.username}',
                    'Student Majors': majors,
                    'Advisor ID': f'{professor.oxy_id}',
                    'Advisor First Name': f'{professor.first_name}',
                    'Advisor Last Name': f'{professor.last_name}',
                    'Advisor Remaining Capacity': f'{professor.advisee_limit - len(matches)}',
                    'Reasons': reasons,
                })
    unbuffered_print(f'INFO: output saved to {output_path}.')


def main():
    args = parse_args()
    divisions = read_divisions(args)
    professors = read_professors(divisions, args)
    students = read_students(divisions, args)
    best_matches = random_restart_hillclimbing(divisions, professors, students, args)
    save_results(best_matches, args.output_path)


if __name__ == '__main__':
    main()
