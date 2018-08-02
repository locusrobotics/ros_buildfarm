<!DOCTYPE html>
<html>
<head>
  <title>@title - @start_time_local_str</title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>

  <script type="text/javascript" src="js/moment.min.js"></script>
  <script type="text/javascript" src="js/zepto.min.js"></script>
  <script type="text/javascript">
    window.META_COLUMNS = 4;
  </script>
  <script type="text/javascript" src="js/setup.js?@(resource_hashes['setup.js'])"></script>

  <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.1.0/css/all.css" integrity="sha384-lKuwvrZot6UHsBSfcMvOkWwlCMgc0TaWr+30HWe3a4ltaBwTZhyTEggF5tJv8tbt" crossorigin="anonymous">
  <link rel="stylesheet" type="text/css" href="css/status_page.css?@(resource_hashes['status_page.css'])" />
  <link rel="stylesheet" type="text/css" href="css/compare_page.css?@(resource_hashes['compare_page.css'])" />
</head>
@{
def status_cell(status):
    if not status:
        return '<td></td>'
    css_class = ''
    if status == 'released':
        css_class = status
    elif 'waiting' in status:
        css_class = 'waiting'
    elif 'source' in status:
        css_class = 'source'
    elif 'build' in status:
        css_class = 'broken'
    elif 'complicated' in status:
        css_class = 'complicated'
    return '<td class="{} status" title="{}"></td>'.format(css_class, status)
}
<body>
  <script type="text/javascript">
    window.body_ready_with_age(moment.duration(moment() - moment("@start_time", "X")));
  </script>
  <div class="top logo search">
    <h1><img src="http://wiki.ros.org/custom/images/ros_org.png" alt="ROS.org" width="150" height="32" /></h1>
    <h2>@title</h2>
    <p>Quick filter:
      <a href="?q=" title="Show all packages">*</a>,
      <a href="?q=RELEASED">RELEASED</a>,
      <a href="?q=WAITING">WAITING</a>,
      <a href="?q=SOURCE_PROBLEM">SOURCE_PROBLEM</a>,
      <a href="?q=BROKEN">BROKEN</a>,
      <a href="?q=COMPLICATED">COMPLICATED</a>
    </p>
    <form action="?">
      <input type="text" name="q" id="q" title="A query string can contain multiple '+' separated parts which must all be satisfied. Each part can also be a RegExp (e.g. to combine two parts with 'OR': 'foo|bar'), but can't contain '+'." />
      <p id="search-count"></p>
    </form>
  </div>
  <div class="top legend">
    <ul class="squares">
      <li class="released status">Released
      <li class="waiting status">Waiting for Release
      <li class="source status">Problem with Source
      <li class="broken status">Broken
      <li class="complicated status">Complicated
    </ul>
  </div>
  <div class="top age">
    <p>This should show the age of the page...</p>
  </div>
  <table>
    <caption></caption>
    <thead>
      <tr>
        <th class="sortable"><div>Package</div></th>
        <th class="sortable"><div>Organization</div></th>
        <th class="sortable"><div>Repo</div></th>
        <th><div>Maintainers</div>
@[for rosdistro_name in rosdistro_names]@
        <th><div class="distro" title="@rosdistro_name.capitalize()">@rosdistro_name[0].capitalize()</div></th>
@[end for]@
        <th>
    </thead>
    <tbody>
    @[for org in sorted(super_status, key=lambda d: str(d).lower())]@
        @{ org_link = '<a href="%s">%s</a>' % (super_status[org]['url'], org) if ('url' in super_status[org]) else org }@
        @[for repo in sorted(super_status[org]['repos'])]@
            @[for pkg in sorted(super_status[org]['repos'][repo]['pkgs'])]@
            @{ PKG = super_status[org]['repos'][repo]['pkgs'][pkg] }@
            <tr><td class="pkg">@pkg
                <td><div>@org_link</div>
                <td><div><a href="@super_status[org]['repos'][repo]['url']">@repo</a></div>
                <td><div>@[for email, name in PKG['maintainers'].items() ]@
                    <a href="mailto:@email">@name.encode('ascii', 'xmlcharrefreplace')</a><br />
                    @[end for]@</div>
                @[for distro in rosdistro_names]@
                @status_cell(PKG['status'].get(distro))
                @[end for]@
                <td style="position:relative; text-align: right">
                  <span class="expand_button status" onclick="expand(this)">
                    <span class="moreinfo">
                        @[for distro in rosdistro_names]@
                        @[if distro in PKG['status'] ]@
                        <b>@distro</b>: @PKG['status'][distro]
                                        (@PKG['versions'][distro])<br />
                        @[end if]@
                        @[end for]@
                    </span>
                  </span>
                </td>
            </tr>
            @[end for]@
        @[end for]@
    @[end for]@
    </tbody>

    <script type="text/javascript">
        window.tbody_ready();
    </script>
  </table>
  <script type="text/javascript">window.body_done();</script>
</body>
</html>
