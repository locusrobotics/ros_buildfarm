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
def status_cell(status, version):
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
    return '<td class="{} status" title="{} {}"></td>'.format(css_class, version, status)
}
<body>
  <script type="text/javascript">
    window.age_threshold_green = moment.duration(7, 'hours');
    window.body_ready_with_age(moment.duration(moment() - moment("@start_time", "X")));
  </script>
  <div class="top logo">
    <h1><img src="http://wiki.ros.org/custom/images/ros_org.png" alt="ROS.org" width="150" height="32" /></h1>
    <h2>@title</h2>
  </div>
  <div class="top search">
    <form action="?">
      <input type="text" name="q" id="q" title="A query string can contain multiple '+' separated parts which must all be satisfied. Each part can also be a RegExp (e.g. to combine two parts with 'OR': 'foo|bar'), but can't contain '+'." />
      <p>Quick filter:
        <a href="?q=" title="Show all packages">*</a>,
        <a href="?q=DIFF_PATCH" title="Filter packages which are only differ in the patch version">different patch version</a>,
        <a href="?q=DOWNGRADE_VERSION" title="Filter packages which disappear by a sync from shadow-fixed to public">downgrade</a>,
        <a href="?q=DIFF_BRANCH_SAME_VERSION" title="Filter packages which are are released from different branches but have same minor version">same version from different branches</a>
      </p>
      <p id="search-count"></p>
    </form>
  </div>
  <div class="top age">
    <p>This should show the age of the page...</p>
  </div>
  <table>
    <caption></caption>
    <thead>
      <tr>
        <th class="sortable"><div>Package</div></th>
        <th class="sortable"><div>Repo</div></th>
        <th class="sortable"><div>Maintainers</div></th>
@[for rosdistro_name in rosdistro_names]@
        <th><div class="distro" title="@rosdistro_name.capitalize()">@rosdistro_name[0].capitalize()</div></th>
@[end for]@
        <th>
      </tr>
    </thead>
    <tbody>
@[for pkg_name, row in sorted(pkgs_data.items())]@
      <tr>
        <td><div>@row.pkg_name</div>
        @{ labels = row.get_labels(rosdistro_names) }@
        <td><div>@row.get_repo_name_with_link()
            @[if labels]@
            <span class="ht">@(' '.join(labels))</span>
            @[end if]
            </div>
        <td><div>@row.get_maintainers()</div>
        @[for distro in rosdistro_names]@
        @status_cell(row.status.get(distro), row.versions.get(distro))
        @[end for]@
        <td style="position:relative; text-align: right">
          <span class="expand_button status" onclick="expand(this)">
            <span class="moreinfo">
                @[for distro in rosdistro_names]@
                @[if distro in row.versions ]@
                <b>@distro</b>: @row.status.get(distro, '')
                                (@row.versions[distro])<br />
                @[end if]@
                @[end for]@
            </span>
          </span>
        </td>

@[end for]@
    </tbody>

    <script type="text/javascript">
        window.tbody_ready();
    </script>
  </table>
  <script type="text/javascript">window.body_done();</script>
</body>
</html>
