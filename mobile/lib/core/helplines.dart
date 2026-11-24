/// Helplines shown on the "Get help" sheet.
///
/// TODO(team): verify every number before the demo, and add the college
/// counselling cell. Later these come from GET /resources?type=helpline.
class Helpline {
  const Helpline(this.name, this.phone, this.note);
  final String name;
  final String phone;
  final String note;
}

const helplines = <Helpline>[
  Helpline('Tele-MANAS (national)', '14416', '24×7, free, multiple languages'),
  Helpline('Emergency services', '112', 'If you are in immediate danger'),
];
