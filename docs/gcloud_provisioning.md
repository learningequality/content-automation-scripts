
Command line provisioning
=========================

  - Install command line tools https://cloud.google.com/sdk/
  - Run `gcloud init` which will result in a long dialog:

        You must log in to continue. Would you like to log in (Y/n)?  Y
        You are logged in as: ...

        Pick cloud project to use:
        ...
        [?] kolibri-demo-servers
        ...
        Please enter numeric choice or text value   ?
        Your current project has been set to: [kolibri-demo-servers].
        Do you want to configure Google Compute Engine
        (https://cloud.google.com/compute) settings (Y/n)?  Y
        Which Google Compute Engine zone would you like to use as project
        default?
        If you do not specify a zone via a command line flag while working
        with Compute Engine resources, the default is assumed.
          ...
          [23] us-east1-d
        Your project default Compute Engine zone has been set to [us-east1-d].
        You can change it by running [gcloud config set compute/zone NAME].
        Your project default Compute Engine region has been set to [us-east1].
        You can change it by running [gcloud config set compute/region NAME].
        Created a default .boto configuration file at [/Users/ivan/.boto]. See this file and
        [https://cloud.google.com/storage/docs/gsutil/commands/config] for more
        information about configuring Google Cloud Storage.
        Your Google Cloud SDK is configured and ready to use!
        * Commands that require authentication will use ... by default
        * Commands will reference project `kolibri-demo-servers` by default
        * Compute Engine commands will use region `us-east1` by default
        * Compute Engine commands will use zone `us-east1-d` by default
        Run `gcloud help config` to learn how to change individual settings

