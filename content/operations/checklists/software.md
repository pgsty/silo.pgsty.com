---
title: "Software Checklist"
url: "/operations/checklists/software/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/checklists/software.rst
upstream_modified: false
---

<a id="software-checklist"></a>
<a id="minio-software-checklists"></a>

Use the following checklist when planning the software configuration for a production, distributed MinIO deployment.

## MinIO Pre-requisites {#minio-pre-requisites}

<table>
  <tbody>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Servers running a Linux operating system with a 6.6+ kernel. Red Hat Enterprise Linux (RHEL) 10 or Ubuntu LTS 22.04.01+ ship with these Kernel’s by default.
Ensure the chosen OS uses LTS and in-support releases of a 6.6+ Linux kernel.</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>A method to synchronize time servers across nodes, such as with <code>ntp</code>, <code>timedatectl</code> or <code>timesyncd</code>.
The method to use varies by operating system.
Check with your operating system’s documentation for how to synchronize time with a time server.</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Disable system services that index, scan, or audit the filesystem, system-level calls, or kernel-level calls.
These services can reduce performance due to resource contention or interception of MinIO operations.</p><p>MinIO strongly recommends uninstalling or disabling the following services on hosts running MinIO:</p><ul><li><p><code>mlocate</code> or <code>plocate</code></p></li><li><p><code>updatedb</code></p></li><li><p><code>auditd</code></p></li><li><p>Crowdstrike Falcon</p></li><li><p>Antivirus software (<code>clamav</code>)</p></li></ul><p>The above list represents the most common services or softwares known to cause performance or behavioral issues with high performance systems like MinIO.
Consider removing or disabling any other service or software which functions similarly to those listed above on MinIO hosts.</p><p>Alternatively, configure these services to ignore or exclude the MinIO Server process and <em>all</em> drives or drive paths accessed by MinIO.</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>System administrator access to the remote servers</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>A management tool for distributed systems, such as Ansible, Terraform, or Kubernetes for orchestrated environments.
Kubernetes infrastructures should use the MinIO Operator for best results.</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Load balancer to handle routing of requests (for example, <a href="https://www.nginx.com/">NGINX</a>)</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p><a href="/operations/monitoring/collect-minio-metrics-using-prometheus/#minio-metrics-collect-using-prometheus">Prometheus</a> or a Prometheus-compatible setup for monitoring and metrics</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p><a href="/operations/monitoring/grafana/#minio-grafana">Grafana configured</a> for dashboards</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>(optional) <a href="/reference/minio-mc/#command-mc"><code>mc</code></a> installed on the local host system</p></td>
    </tr>
  </tbody>
</table>

## MinIO Install {#minio-install}

Install a matching version of MinIO across all nodes in the deployment.

## Post Install Tasks {#post-install-tasks}

<table>
  <tbody>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>(optional) Create an <a href="/reference/minio-mc/mc-alias/#command-mc.alias"><code>mc alias</code></a> for each server with <a href="/reference/minio-mc/mc-alias-set/#command-mc.alias.set"><code>mc alias set</code></a> from your local machine for command line access to work with the MinIO deployment from a local machine</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Configure <a href="/administration/bucket-replication/bucket-replication-requirements/#minio-bucket-replication-requirements">Bucket replication</a> to duplicate contents of a bucket to another bucket location</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Configure <a href="/operations/replication/multi-site-replication/#minio-site-replication-overview">Site replication</a> to synchronize contents of multiple dispersed data center locations</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Configure <a href="/administration/object-management/object-lifecycle-management/#minio-lifecycle-management">Object retention rules with lifecycle management</a> to manage when objects should expire</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Configure <a href="/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering">Object storage level rules with tiering</a> to move objects between hot, warm, and cold storage and maximize storage cost efficiencies</p></td>
    </tr>
  </tbody>
</table>

> [!NOTE]
> **Exclusive access to drives**
>
> MinIO **requires** *exclusive* access to the drives or volumes provided for object storage. No other processes, software, scripts, or persons should perform *any* actions directly on the drives or volumes provided to MinIO or the objects or files MinIO places on them.
>
> Unless directed by MinIO Engineering, do not use scripts or tools to directly modify, delete, or move any of the data shards, parity shards, or metadata files on the provided drives, including from one drive or node to another. Such operations are very likely to result in widespread corruption and data loss beyond MinIO’s ability to heal.

## 3rd Party Identity Provider Tasks {#rd-party-identity-provider-tasks}

<table>
  <tbody>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td>Authenticate to MinIO with <a href="/developers/security-token-service/#minio-security-token-service">Security Token Service (STS)</a><br />Enabling this requires MinIO support.<br /></td>
    </tr>
  </tbody>
</table>
