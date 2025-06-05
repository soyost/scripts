#! /bin/zsh
# Source: https://confluence.oraclecorp.com/confluence/display/OHAI/Simultaneous+Cerner+and+Oracle+VPN+connections+with+OpenConnect+and+vpn-slice
# Make sure to check back regularly as host patterns are updated from time to time.
 
openconnect_path=`readlink -f $(which openconnect) | sed -r 's/(.*)\/bin\/openconnect/\1/'`
vpn_url=https://myaccess.oraclevpn.com
csd_user="nobody" # for security purposes
useragent="AnyConnect"
  
hosts="{artifacthub-phx,artifactory,artifactory-builds,atlas,bitbucket,confluence,devops,devops-next,devops-gamma,grafana,jira,orahub,permissions}.oci.oraclecorp.com \
devops.us-phoenix-1.oci.oraclecloud.com  \
{odo-docker-signed-local,oicng-docker-local}.artifactory.oci.oraclecorp.com \
{iad-c-csec-awp-01.us6,phx-c-csec-awp-01.us5}.oraclecloud.com \
ehrc-test-instance-1.opadev.process.us-ashburn-1.oci.oracleiaas.com \
fido-login-int.identity.oraclecloud.com \
horizonoac-idkzdoic6acl-ia.analytics.ocp.oraclecloud.com \
{agents,aiservicesdemo,alm,apex,aru,badge,bug,cloudnav,confluence,cssap,docs.gcn,ensemble,entapex,entapex-dev,esource,exchange,gbuconfluence,gbujira,globalmarketingapp,global-apex,global-ebusiness,hrservices,iambi,internal-docs,ip,jira,managers,mdpromocatalog,mydesktop,naaorgappsdev,news,ocp,ogra,ohaicrossword,ohaiphishingquiz,ohaitrivia,ohaitriviabackend,oim,printers,ptp,recruit,securitytimes,securitytimes-admin,telco,vpat}.oraclecorp.com \
{facts,pls,pls-uat,rmsdwh,rmsoac,gbublackduck,xgbu-ace-wtss,oscsoci}.appoci.oraclecorp.com \
jira-sd.mc1.oracleiaas.com \
{login,u2f-validator}.idp.mc1.oracleiaas.com \
login.us-phoenix-1.idp.mc1.oracleiaas.com \
oci.private.devops.scmservice.us-phoenix-1.oci.oracleiaas.com \
{database,goto,mts-mmprod-ds,omm,orca,pls,slc18zlg,surl,cloudlab,ci-cloud}.us.oracle.com \
{ch3,ch4}-c-sec-awp-01.us2.oraclecloud.com=10.23.226.53 \
licoel79-8.licdsiphx.peocorpphxssv1.oraclevcn.com \
oracle.com \
{gps,gxpap,my,s2shelp}.oracle.com \
ora-hr.custhelp.com"
  
sudo openconnect $vpn_url --csd-user=$csd_user --csd-wrapper="$openconnect_path/libexec/openconnect/csd-post.sh" --useragent="$useragent" --gnutls-priority="NORMAL:-VERS-ALL:+VERS-TLS1.2:+RSA:+AES-128-CBC:+SHA1" -s "vpn-slice $hosts"